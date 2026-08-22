# Autonomous Email-to-Action Agent

An agent that reads a simulated inbox, classifies each email's intent, and
takes a distinct autonomous action per intent — with a full audit trail
explaining every decision.

## Intents handled

| Intent               | Signal examples                                  | Autonomous action |
|-----------------------|---------------------------------------------------|--------------------|
| `invoice_submission`  | "invoice attached", "amount due", "net 30"        | Logs the invoice into `invoice_ledger.json`, drafts an acknowledgement reply |
| `payment_query`       | "status of payment", "expected payment date"      | Looks up (simulated) payment status, drafts a status reply |
| `dispute`              | "dispute", "overcharge", "escalate", "legal"      | Creates a prioritized escalation task for the finance team, drafts a holding reply |
| `spam`                 | "you have won", "click here", "% off"             | Quarantines the sender, no reply sent, no ledger/task created |
| `needs_review` (ambiguous) | low confidence / weak or conflicting signals | Creates a human-review task with the reasoning attached; **no reply is auto-sent** |

Two emails in the sample inbox (`EMAIL-006`, `EMAIL-007`) are intentionally
ambiguous/borderline and are routed to `needs_review` rather than force-classified —
that's the required "handle at least one ambiguous email" behavior.

## Architecture

```
data/sample_emails.json   <- simulated inbox
        |
        v
src/classifier.py         <- weighted keyword scorer -> ClassificationResult
        |                     (intent, confidence, per-intent scores, reasoning)
        v
src/actions.py             <- one handler per intent, each returns
        |                      {action, details}
        v
src/agent.py                <- orchestrator: classify -> act -> log
        |
        v
output/audit_trail.json      <- one row per email: intent, confidence,
                                 reasoning, action taken, action details
output/invoice_ledger.json    <- structured invoice records
output/followup_tasks.json     <- dispute escalations + human-review tasks
output/draft_replies.json      <- drafted reply text (not auto-sent)
```

**Classification approach — hybrid by design.** The default classifier is a
transparent, weighted keyword/rule scorer: fast, deterministic, free, and
fully explainable — every score traces back to specific matched phrases,
which is exactly what an audit trail needs. `src/classifier.py` also has a
`llm_classify()` stub wired into the same `ClassificationResult` interface,
gated behind `EMAIL_AGENT_USE_LLM=true`, so you can swap in a real LLM call
(Claude, Gemini, etc.) for higher accuracy on nuanced or multi-intent emails
without changing anything downstream. This is a deliberate reliability vs.
accuracy tradeoff worth mentioning in your demo video.

**Confidence and ambiguity handling.** An email is routed to `needs_review`
if: (a) its top intent's raw signal is too weak (a single low-weight keyword
match shouldn't be enough to act on, even if it "wins" by ranking), (b) its
normalized confidence is below threshold, or (c) the top two intents are too
close to call. The agent never guesses on a coin-flip — it escalates to a
human instead.

## Run it

```bash
cd email-agent
pip install -r requirements.txt   # no external deps by default
python src/agent.py
```

Console output shows a one-line summary per email; full detail lands in
`output/audit_trail.json`.

## Files produced per run

- `output/audit_trail.json` — the deliverable for "clear audit trail"
- `output/invoice_ledger.json`
- `output/followup_tasks.json`
- `output/draft_replies.json`

---

## Using Google Antigravity to build/extend this (first-time guide)

Antigravity is an agent-first IDE built on VS Code: instead of you writing
every line, you describe outcomes and an agent plans, edits, runs, and
verifies. Here's how to use it well for this project.

### 1. Install & open the project
- Download from antigravity.google, sign in with your Google account.
- On first launch choose **Agent-Assisted Development** mode (not full
  Autopilot) — it lets the agent run terminal commands and edit files but
  keeps you approving major changes, which matters for a submission you'll
  be graded on.
- Open this project folder (`email-agent/`) so Antigravity scopes its
  context correctly — it's project-centric, so file/tool access follows
  the folder you open.

### 2. Good first prompts to the agent
Rather than "build me an email agent" (too vague), give it scoped, verifiable
tasks — this is the difference between a clean result and a mess:
- *"Read src/classifier.py and src/actions.py, then add a sixth email to
  data/sample_emails.json that's genuinely ambiguous between payment_query
  and dispute. Run src/agent.py and show me how it's classified."*
- *"Write a pytest suite in tests/ that checks each of the 10 sample emails
  gets a non-null action in the audit trail, and that the two ambiguous
  emails land in needs_review. Run it and fix any failures."*
- *"Implement llm_classify() in src/classifier.py using the Anthropic
  Messages API, gated behind EMAIL_AGENT_USE_LLM. Don't break the existing
  rule-based path — it should still be the default."*

### 3. Use Plan mode for anything multi-file
For anything touching classifier + actions + agent together, ask it to
produce a Plan Artifact first ("plan this before you touch any files"), review
the plan, then let it execute. This gives you a reviewable trail of *why*
changes were made — useful evidence for your own understanding when you
present it.

### 4. Let the agent verify itself
Antigravity's agents can run your terminal and check output — explicitly ask
it to run `python src/agent.py` after every change and paste back the
console output, so you're not just trusting a diff.

### 5. Push to a repo
Once it's working: `git init`, commit, create a GitHub repo, push. Antigravity
can do this for you if you ask it to ("initialize git, commit with a message
describing the audit trail feature, create and push to a new GitHub repo
named email-to-action-agent") — but double check the remote/visibility
settings yourself before you hit submit.

---

## Demo video script (5 minutes)

**0:00–2:00 — Tech stack & architecture**
- Python, stdlib only by default (call out *why*: zero external deps means
  the demo can never fail on a missing API key or network hiccup).
- Walk through the pipeline diagram above: inbox -> classifier -> action
  dispatch -> audit trail.
- Name the 4+ intents and their distinct actions in one breath.
- Mention the hybrid classifier design and the LLM stub as your "we thought
  about production" signal.

**2:00–4:00 — Live demo**
- Show `data/sample_emails.json` briefly — point out one obvious invoice,
  one obvious spam, and the ambiguous email (EMAIL-007, which reads as
  both a payment_query and a dispute).
- Run `python src/agent.py` live, let the console output stream.
- Open `output/audit_trail.json` and read out 2–3 entries: the intent, the
  confidence, the *reasoning*, and the action taken — this is your strongest
  "completeness of audit trail" evidence.
- Open `output/draft_replies.json` to show a generated reply, and
  `output/followup_tasks.json` to show the escalation/review tasks.

**4:00–5:00 — One design tradeoff**
Pick one and argue it briefly:
- *Rule-based-first vs. LLM-first classification*: rules are explainable,
  free, deterministic, and demo-safe, but brittle on phrasing it hasn't
  seen; LLM classification generalizes better but costs latency, money, and
  introduces non-determinism into an audit trail that's supposed to be
  reproducible. Chose rules as the default, LLM as an opt-in upgrade path.
- *Or*: "never auto-act on ambiguous emails" — a stricter confidence bar
  means more emails land in needs_review than a looser one would produce,
  trading autonomy for safety on financial correspondence, where a wrong
  auto-reply (e.g. telling a customer a disputed invoice is fine) is worse
  than a delay.
