"""
agent.py
--------
Entry point. Reads the inbox, classifies each email, dispatches the
appropriate autonomous action, and writes a full audit trail.

Run:
    python src/agent.py
Outputs (in ./output/):
    audit_trail.json      -- one entry per email: intent, confidence,
                              reasoning, action taken, action details
    invoice_ledger.json    -- logged invoices
    followup_tasks.json    -- dispute escalations + human-review tasks
    draft_replies.json     -- drafted email replies
"""

import json
import os
from datetime import datetime, timezone

from classifier import classify
from actions import ACTION_DISPATCH, handle_needs_review

BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.join(BASE_DIR, "..", "data", "sample_emails.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "output")
AUDIT_FILE = os.path.join(OUTPUT_DIR, "audit_trail.json")


def reset_outputs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for fname in ["audit_trail.json", "invoice_ledger.json", "followup_tasks.json", "draft_replies.json"]:
        path = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(path):
            os.remove(path)


def process_inbox():
    reset_outputs()
    with open(DATA_FILE) as f:
        emails = json.load(f)

    audit_trail = []

    for email in emails:
        result = classify(email)

        if result.intent == "needs_review":
            action_result = handle_needs_review(email, result.reasoning)
        else:
            action_result = ACTION_DISPATCH[result.intent](email)

        audit_entry = {
            "email_id": email["id"],
            "from": email["from"],
            "subject": email["subject"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "classified_intent": result.intent,
            "confidence": round(result.confidence, 3),
            "intent_scores": {k: round(v, 3) for k, v in result.scores.items()},
            "classification_reasoning": result.reasoning,
            "action_taken": action_result["action"],
            "action_details": action_result["details"],
        }
        audit_trail.append(audit_entry)

        print(f"[{email['id']}] {result.intent:<20} conf={result.confidence:.2f}  "
              f"-> {action_result['action']}")

    with open(AUDIT_FILE, "w") as f:
        json.dump(audit_trail, f, indent=2)

    print(f"\nProcessed {len(emails)} emails. Full audit trail written to {AUDIT_FILE}")
    return audit_trail


if __name__ == "__main__":
    process_inbox()
