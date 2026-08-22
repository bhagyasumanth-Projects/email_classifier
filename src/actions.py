"""
actions.py
----------
One distinct, appropriate autonomous action per intent.

  invoice_submission -> log the invoice into a structured ledger + draft an
                         acknowledgement reply to the sender.
  payment_query       -> look up (simulated) payment status + draft a reply
                         with the status.
  dispute              -> create a follow-up/escalation task for the finance
                          team + draft a holding reply to the sender.
  spam                 -> no reply sent; log-and-discard, quarantine sender.
  needs_review          -> create a "human review" task with the ambiguity
                          reasoning attached; draft nothing automatically.

Every action function returns a dict describing exactly what was done,
which becomes a row in the audit trail.
"""

import json
import os
import re
from datetime import datetime, timezone

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
INVOICE_LEDGER = os.path.join(OUTPUT_DIR, "invoice_ledger.json")
TASKS_FILE = os.path.join(OUTPUT_DIR, "followup_tasks.json")
DRAFTS_FILE = os.path.join(OUTPUT_DIR, "draft_replies.json")

# Fake payment status DB used to simulate a real lookup for payment_query intent
MOCK_PAYMENT_STATUS_DB = {
    "INV-3390": {"status": "Scheduled", "pay_date": "2026-08-28"},
    "INV-5502": {"status": "On hold - awaiting invoice correction", "pay_date": None},
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def _append(path, record):
    data = _load(path, [])
    data.append(record)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _extract_amount(text: str):
    match = re.search(r"\$([\d,]+\.\d{2}|\d[\d,]*)", text)
    return match.group(0) if match else "unknown"


def _extract_invoice_id(text: str):
    match = re.search(r"INV-\d+", text, re.IGNORECASE)
    return match.group(0).upper() if match else "UNKNOWN"


def handle_invoice_submission(email: dict) -> dict:
    text = f"{email['subject']} {email['body']}"
    invoice_id = _extract_invoice_id(text)
    amount = _extract_amount(text)
    record = {
        "invoice_id": invoice_id,
        "from": email["from"],
        "amount": amount,
        "email_id": email["id"],
        "logged_at": _now(),
    }
    _append(INVOICE_LEDGER, record)

    reply = {
        "email_id": email["id"],
        "to": email["from"],
        "subject": f"Re: {email['subject']}",
        "body": (
            f"Hi,\n\nThank you for submitting invoice {invoice_id}. We have logged it "
            f"into our accounts payable system for amount {amount}. It will be "
            f"processed per standard payment terms and you will be notified upon "
            f"completion.\n\nBest regards,\nAP Automation"
        ),
        "drafted_at": _now(),
    }
    _append(DRAFTS_FILE, reply)

    return {
        "action": "logged_invoice_and_drafted_acknowledgement",
        "details": f"Invoice {invoice_id} ({amount}) recorded in invoice_ledger.json; "
                    f"acknowledgement reply drafted to {email['from']}.",
    }


def handle_payment_query(email: dict) -> dict:
    text = f"{email['subject']} {email['body']}"
    invoice_id = _extract_invoice_id(text)
    status_info = MOCK_PAYMENT_STATUS_DB.get(
        invoice_id, {"status": "Not found in payment system - forwarding to AP team", "pay_date": None}
    )

    body_lines = [
        f"Hi,\n\nThanks for reaching out about {invoice_id}.",
        f"Current status: {status_info['status']}.",
    ]
    if status_info["pay_date"]:
        body_lines.append(f"Expected payment date: {status_info['pay_date']}.")
    body_lines.append("\nLet us know if you have further questions.\n\nBest regards,\nAP Automation")

    reply = {
        "email_id": email["id"],
        "to": email["from"],
        "subject": f"Re: {email['subject']}",
        "body": "\n".join(body_lines),
        "drafted_at": _now(),
    }
    _append(DRAFTS_FILE, reply)

    return {
        "action": "looked_up_status_and_drafted_reply",
        "details": f"Queried payment status for {invoice_id} "
                    f"({status_info['status']}); reply drafted to {email['from']}.",
    }


def handle_dispute(email: dict) -> dict:
    text = f"{email['subject']} {email['body']}"
    invoice_id = _extract_invoice_id(text)
    urgency = "high" if any(w in text.lower() for w in ["legal", "urgent", "third email", "5 business days"]) else "normal"

    task = {
        "email_id": email["id"],
        "type": "dispute_escalation",
        "invoice_id": invoice_id,
        "assigned_to": "finance_team",
        "priority": urgency,
        "summary": email["subject"],
        "created_at": _now(),
    }
    _append(TASKS_FILE, task)

    reply = {
        "email_id": email["id"],
        "to": email["from"],
        "subject": f"Re: {email['subject']}",
        "body": (
            f"Hi,\n\nThank you for flagging this. We've escalated the dispute on "
            f"{invoice_id} to our finance team for review (priority: {urgency}). "
            f"Someone will follow up with you directly within 2 business days.\n\n"
            f"Best regards,\nAP Automation"
        ),
        "drafted_at": _now(),
    }
    _append(DRAFTS_FILE, reply)

    return {
        "action": "created_escalation_task_and_drafted_holding_reply",
        "details": f"Dispute on {invoice_id} escalated to finance_team "
                    f"(priority={urgency}); holding reply drafted to {email['from']}.",
    }


def handle_spam(email: dict) -> dict:
    return {
        "action": "quarantined_no_reply",
        "details": f"Sender {email['from']} flagged as spam; no reply sent, "
                    f"email excluded from ledgers/tasks.",
    }


def handle_needs_review(email: dict, reasoning: str) -> dict:
    task = {
        "email_id": email["id"],
        "type": "human_review",
        "from": email["from"],
        "subject": email["subject"],
        "reason": reasoning,
        "created_at": _now(),
    }
    _append(TASKS_FILE, task)
    return {
        "action": "flagged_for_human_review",
        "details": f"Ambiguous intent -- created human-review task instead of "
                    f"guessing. Reason: {reasoning}",
    }


ACTION_DISPATCH = {
    "invoice_submission": handle_invoice_submission,
    "payment_query": handle_payment_query,
    "dispute": handle_dispute,
    "spam": handle_spam,
    # needs_review handled specially in agent.py because it needs the reasoning string
}
