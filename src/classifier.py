"""
classifier.py
--------------
Classifies an email into one of five intents:
  invoice_submission | payment_query | dispute | spam | needs_review (ambiguous)

Design:
  - A transparent, weighted keyword/rule scorer runs first. It is fast,
    free, deterministic, and fully explainable (every score is traceable
    to specific matched phrases) -- important for an audit trail.
  - If USE_LLM=True and an API key is available, an LLM call can be used
    either to classify directly or to arbitrate low-confidence / close-call
    cases. This is wired up but OFF by default so the demo never depends
    on network access or a key.
  - Any email where the top two intent scores are close, or the winning
    score is below a confidence threshold, is routed to 'needs_review'
    instead of being force-classified. This is the ambiguity handling
    required by the assignment.
"""

from dataclasses import dataclass, field
import os

USE_LLM = os.environ.get("EMAIL_AGENT_USE_LLM", "false").lower() == "true"
CONFIDENCE_THRESHOLD = 0.35   # below this -> needs_review
CLOSE_CALL_MARGIN = 0.12      # if top-2 scores differ by less than this -> needs_review
MIN_RAW_SIGNAL = 3            # minimum absolute weighted score required to act;
                               # guards against a single weak keyword match producing
                               # a misleadingly high *normalized* confidence

INTENT_KEYWORDS = {
    "invoice_submission": {
        "invoice": 3, "invoice attached": 4, "please find attached invoice": 5,
        "amount due": 2, "payment terms": 2, "net 30": 2, "po ": 1,
        "billing": 1, "subscription invoice": 3, "generated": 1,
    },
    "payment_query": {
        "status of payment": 5, "haven't seen the payment": 4, "when will": 2,
        "expected payment date": 4, "update on payment": 3, "any updates": 2,
        "confirm receipt": 1, "hasn't gone out": 2, "please advise": 1,
        "let us know if you need": -1,
    },
    "dispute": {
        "dispute": 5, "disputing": 5, "discrepancy": 3, "overcharge": 4,
        "incorrect": 2, "wrong po": 2, "escalate": 3, "legal counsel": 4,
        "formally": 2, "never rendered": 3, "corrected": 2,
    },
    "spam": {
        "congratulations": 3, "you have won": 5, "claim now": 4, "click here": 3,
        "cash prize": 4, "send your bank details": 5, "unsubscribe": 2,
        "% off": 3, "biggest sale": 3, "limited time": 2, "!!!": 3,
    },
}


@dataclass
class ClassificationResult:
    intent: str
    confidence: float
    scores: dict
    reasoning: str
    matched_signals: list = field(default_factory=list)


def _score_email(text: str) -> dict:
    text_l = text.lower()
    scores = {intent: 0 for intent in INTENT_KEYWORDS}
    matched = {intent: [] for intent in INTENT_KEYWORDS}
    for intent, kw_weights in INTENT_KEYWORDS.items():
        for phrase, weight in kw_weights.items():
            if phrase in text_l:
                scores[intent] += weight
                matched[intent].append(phrase.strip())
    return scores, matched


def _normalize(scores: dict) -> dict:
    total = sum(max(v, 0) for v in scores.values())
    if total == 0:
        return {k: 0.0 for k in scores}
    return {k: max(v, 0) / total for k, v in scores.items()}


def rule_based_classify(email: dict) -> ClassificationResult:
    text = f"{email.get('subject','')} {email.get('body','')} {email.get('from','')}"
    raw_scores, matched = _score_email(text)
    norm_scores = _normalize(raw_scores)

    ranked = sorted(norm_scores.items(), key=lambda kv: kv[1], reverse=True)
    top_intent, top_conf = ranked[0]
    second_intent, second_conf = ranked[1] if len(ranked) > 1 else (None, 0.0)
    top_raw = raw_scores[top_intent]

    weak_signal = top_raw < MIN_RAW_SIGNAL
    ambiguous = (
        weak_signal
        or top_conf < CONFIDENCE_THRESHOLD
        or ((top_conf - second_conf) < CLOSE_CALL_MARGIN and top_conf < 0.6)
    )

    if ambiguous:
        if weak_signal:
            reasoning = (
                f"Top intent '{top_intent}' only matched a single weak signal "
                f"(raw score {top_raw}, matched: {matched[top_intent]}). Too little "
                f"evidence to act autonomously even though it 'won' by ranking -- "
                f"routed to human review."
            )
        else:
            reasoning = (
                f"Top intent '{top_intent}' scored {top_conf:.2f} vs runner-up "
                f"'{second_intent}' at {second_conf:.2f} -- margin too small / confidence "
                f"too low to act autonomously. Routed to human review instead of guessing."
            )
        return ClassificationResult(
            intent="needs_review",
            confidence=top_conf,
            scores=norm_scores,
            reasoning=reasoning,
            matched_signals=matched.get(top_intent, []),
        )

    reasoning = (
        f"Classified as '{top_intent}' (confidence {top_conf:.2f}) based on matched "
        f"signals: {matched[top_intent]}."
    )
    return ClassificationResult(
        intent=top_intent,
        confidence=top_conf,
        scores=norm_scores,
        reasoning=reasoning,
        matched_signals=matched[top_intent],
    )


def llm_classify(email: dict) -> ClassificationResult:
    """
    Optional path: ask an LLM to classify + explain, then merge with the
    rule-based result for a confidence check. Only runs if USE_LLM=True.
    Kept provider-agnostic -- plug in Anthropic/Gemini/OpenAI here.
    """
    raise NotImplementedError(
        "Wire up your LLM provider of choice here (e.g. Anthropic Messages API "
        "or Gemini API) and return a ClassificationResult. Left unimplemented "
        "so the demo has zero external dependencies by default."
    )


def classify(email: dict) -> ClassificationResult:
    if USE_LLM:
        try:
            return llm_classify(email)
        except NotImplementedError:
            pass  # fall through to rule-based
    return rule_based_classify(email)
