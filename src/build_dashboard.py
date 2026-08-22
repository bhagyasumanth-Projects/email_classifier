"""
build_dashboard.py
------------------
Reads audit_trail.json, invoice_ledger.json, followup_tasks.json, draft_replies.json,
and sample_emails.json to generate a single self-contained, dark-themed HTML ops console
at output/dashboard.html. Standard library only.
"""

import json
import os
import html
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(__file__)
DATA_FILE = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "sample_emails.json"))
OUTPUT_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "output"))
AUDIT_FILE = os.path.join(OUTPUT_DIR, "audit_trail.json")
INVOICE_LEDGER = os.path.join(OUTPUT_DIR, "invoice_ledger.json")
TASKS_FILE = os.path.join(OUTPUT_DIR, "followup_tasks.json")
DRAFTS_FILE = os.path.join(OUTPUT_DIR, "draft_replies.json")
DASHBOARD_FILE = os.path.join(OUTPUT_DIR, "dashboard.html")

INTENT_CONFIG = {
    "invoice_submission": {
        "label": "Invoice Submission",
        "color": "#38bdf8",
        "bg": "rgba(56, 189, 248, 0.12)",
        "border": "#0284c7",
        "badge_bg": "rgba(56, 189, 248, 0.2)",
    },
    "payment_query": {
        "label": "Payment Query",
        "color": "#fbbf24",
        "bg": "rgba(251, 191, 36, 0.12)",
        "border": "#d97706",
        "badge_bg": "rgba(251, 191, 36, 0.2)",
    },
    "dispute": {
        "label": "Dispute",
        "color": "#f87171",
        "bg": "rgba(248, 113, 113, 0.12)",
        "border": "#dc2626",
        "badge_bg": "rgba(248, 113, 113, 0.2)",
    },
    "spam": {
        "label": "Spam",
        "color": "#9ca3af",
        "bg": "rgba(156, 163, 175, 0.12)",
        "border": "#4b5563",
        "badge_bg": "rgba(156, 163, 175, 0.2)",
    },
    "needs_review": {
        "label": "Needs Review",
        "color": "#c084fc",
        "bg": "rgba(192, 132, 252, 0.12)",
        "border": "#9333ea",
        "badge_bg": "rgba(192, 132, 252, 0.2)",
    },
}


def load_json(path, default=None):
    if default is None:
        default = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {path}: {e}")
    return default


def generate_dashboard():
    sample_emails = load_json(DATA_FILE)
    audit_trail = load_json(AUDIT_FILE)
    invoice_ledger = load_json(INVOICE_LEDGER)
    tasks = load_json(TASKS_FILE)
    drafts = load_json(DRAFTS_FILE)

    email_map = {e["id"]: e for e in sample_emails}
    draft_map = {d["email_id"]: d for d in drafts}

    total_emails = len(audit_trail)
    run_timestamp = (
        audit_trail[0].get("timestamp", datetime.now(timezone.utc).isoformat())
        if audit_trail
        else datetime.now(timezone.utc).isoformat()
    )

    intent_counts = {intent: 0 for intent in INTENT_CONFIG}
    for entry in audit_trail:
        intent = entry.get("classified_intent", "needs_review")
        if intent in intent_counts:
            intent_counts[intent] += 1
        else:
            intent_counts[intent] = 1

    # Build Stat Cards HTML
    stat_cards_html = ""
    for intent, cfg in INTENT_CONFIG.items():
        count = intent_counts.get(intent, 0)
        pct = (count / total_emails * 100) if total_emails > 0 else 0
        stat_cards_html += f"""
        <div class="stat-card" style="border-top: 3px solid {cfg['color']};">
            <div class="stat-header">
                <span class="stat-title">{cfg['label']}</span>
                <span class="stat-badge" style="color: {cfg['color']}; background: {cfg['badge_bg']};">{count}</span>
            </div>
            <div class="stat-value" style="color: {cfg['color']};">{count}</div>
            <div class="stat-subtitle">{pct:.0f}% of total inbox ({total_emails})</div>
            <div class="progress-bg">
                <div class="progress-fill" style="width: {pct:.1f}%; background-color: {cfg['color']};"></div>
            </div>
        </div>
        """

    # Build Email Cards HTML
    email_cards_html = ""
    for entry in audit_trail:
        eid = entry["email_id"]
        intent = entry.get("classified_intent", "needs_review")
        cfg = INTENT_CONFIG.get(intent, INTENT_CONFIG["needs_review"])
        conf = entry.get("confidence", 0.0)
        conf_pct = conf * 100
        original_email = email_map.get(eid, {})
        draft = draft_map.get(eid)

        email_from = html.escape(entry.get("from", original_email.get("from", "N/A")))
        email_subject = html.escape(entry.get("subject", original_email.get("subject", "N/A")))
        email_body = html.escape(original_email.get("body", ""))
        reasoning = html.escape(entry.get("classification_reasoning", ""))
        action_taken = html.escape(entry.get("action_taken", ""))
        action_details = html.escape(entry.get("action_details", ""))

        draft_html = ""
        if draft:
            draft_to = html.escape(draft.get("to", ""))
            draft_subj = html.escape(draft.get("subject", ""))
            draft_body = html.escape(draft.get("body", ""))
            draft_html = f"""
            <div class="draft-box">
                <div class="draft-title">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                        <polyline points="22,6 12,13 2,6"></polyline>
                    </svg>
                    Drafted Auto-Reply
                </div>
                <div class="draft-meta"><strong>To:</strong> {draft_to}</div>
                <div class="draft-meta"><strong>Subject:</strong> {draft_subj}</div>
                <div class="draft-body">{draft_body}</div>
            </div>
            """

        email_cards_html += f"""
        <div class="email-card" style="border-left: 4px solid {cfg['color']};">
            <div class="email-header">
                <div class="email-id-group">
                    <span class="email-id">{eid}</span>
                    <span class="intent-badge" style="color: {cfg['color']}; background: {cfg['badge_bg']}; border: 1px solid {cfg['border']};">
                        {cfg['label']}
                    </span>
                </div>
                <div class="confidence-group">
                    <span class="conf-text">Confidence: <strong>{conf_pct:.1f}%</strong></span>
                    <div class="conf-bar-bg">
                        <div class="conf-bar-fill" style="width: {conf_pct:.1f}%; background-color: {cfg['color']};"></div>
                    </div>
                </div>
            </div>

            <div class="email-meta-row">
                <div><span class="meta-label">From:</span> <span class="meta-val">{email_from}</span></div>
                <div><span class="meta-label">Subject:</span> <span class="meta-val">{email_subject}</span></div>
            </div>

            <div class="email-body-box">
                <div class="box-label">Email Body</div>
                <div class="body-text">{email_body}</div>
            </div>

            <div class="details-grid">
                <div class="reasoning-box">
                    <div class="box-label" style="color: {cfg['color']};">Classification Reasoning</div>
                    <div class="reasoning-text">{reasoning}</div>
                </div>
                <div class="action-box">
                    <div class="box-label">Action Taken</div>
                    <div class="action-code">{action_taken}</div>
                    <div class="action-desc">{action_details}</div>
                </div>
            </div>

            {draft_html}
        </div>
        """

    # Build Invoice Ledger Table
    invoice_rows = ""
    for inv in invoice_ledger:
        iid = html.escape(inv.get("invoice_id", ""))
        eid = html.escape(inv.get("email_id", ""))
        from_addr = html.escape(inv.get("from", ""))
        amt = html.escape(inv.get("amount", ""))
        logged = html.escape(inv.get("logged_at", ""))
        invoice_rows += f"""
        <tr>
            <td><code class="code-badge">{iid}</code></td>
            <td><span class="email-id-sm">{eid}</span></td>
            <td>{from_addr}</td>
            <td class="amount-val">{amt}</td>
            <td class="time-val">{logged}</td>
        </tr>
        """

    if not invoice_rows:
        invoice_rows = '<tr><td colspan="5" class="empty-cell">No invoice entries recorded.</td></tr>'

    # Build Tasks Table
    task_rows = ""
    for t in tasks:
        ttype = t.get("type", "")
        eid = html.escape(t.get("email_id", ""))
        created = html.escape(t.get("created_at", ""))

        if ttype == "dispute_escalation":
            type_badge = f'<span class="task-badge dispute-badge">Dispute Escalation</span>'
            inv_id = html.escape(t.get("invoice_id", ""))
            priority = html.escape(t.get("priority", "normal"))
            target_str = f"Invoice: {inv_id} | Priority: <strong class='prio-{priority}'>{priority.upper()}</strong>"
            summary_str = html.escape(t.get("summary", ""))
        else:
            type_badge = f'<span class="task-badge review-badge">Human Review</span>'
            from_addr = html.escape(t.get("from", ""))
            target_str = f"From: {from_addr}"
            summary_str = html.escape(t.get("reason", ""))

        task_rows += f"""
        <tr>
            <td>{type_badge}</td>
            <td><span class="email-id-sm">{eid}</span></td>
            <td>{target_str}</td>
            <td>{summary_str}</td>
            <td class="time-val">{created}</td>
        </tr>
        """

    if not task_rows:
        task_rows = '<tr><td colspan="5" class="empty-cell">No follow-up or review tasks recorded.</td></tr>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AP Email Classifier Console</title>
    <style>
        :root {{
            --bg-main: #0b0f19;
            --bg-card: #151c2c;
            --bg-input: #1e293b;
            --border-color: #27354a;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --font-main: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-main);
            color: var(--text-primary);
            font-family: var(--font-main);
            line-height: 1.5;
            padding: 24px;
            max-width: 1400px;
            margin: 0 auto;
        }}

        /* Header */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 24px;
        }}

        .brand-title {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .brand-title h1 {{
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: #ffffff;
        }}

        .status-dot {{
            width: 10px;
            height: 10px;
            background-color: #10b981;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #10b981;
        }}

        .header-meta {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-align: right;
        }}

        .header-meta strong {{
            color: var(--text-primary);
        }}

        /* Section Headings */
        .section-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 16px;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        /* Stat Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}

        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .stat-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .stat-title {{
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .stat-badge {{
            font-size: 0.75rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 12px;
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            margin: 8px 0 4px 0;
            font-family: var(--font-mono);
        }}

        .stat-subtitle {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}

        .progress-bg {{
            height: 4px;
            background: var(--bg-input);
            border-radius: 2px;
            overflow: hidden;
        }}

        .progress-fill {{
            height: 100%;
            border-radius: 2px;
        }}

        /* Email Stream */
        .email-cards-container {{
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-bottom: 40px;
        }}

        .email-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            transition: transform 0.15s ease, border-color 0.15s ease;
        }}

        .email-card:hover {{
            border-color: #3b82f6;
        }}

        .email-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}

        .email-id-group {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .email-id {{
            font-family: var(--font-mono);
            font-weight: 700;
            font-size: 0.95rem;
            color: #ffffff;
            background: var(--bg-input);
            padding: 4px 10px;
            border-radius: 4px;
            border: 1px solid var(--border-color);
        }}

        .intent-badge {{
            font-size: 0.75rem;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        .confidence-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .conf-text {{
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}

        .conf-bar-bg {{
            width: 80px;
            height: 6px;
            background: var(--bg-input);
            border-radius: 3px;
            overflow: hidden;
        }}

        .conf-bar-fill {{
            height: 100%;
            border-radius: 3px;
        }}

        .email-meta-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            font-size: 0.88rem;
            margin-bottom: 12px;
            background: rgba(15, 23, 42, 0.4);
            padding: 8px 12px;
            border-radius: 6px;
        }}

        .meta-label {{
            color: var(--text-muted);
            font-weight: 500;
        }}

        .meta-val {{
            color: var(--text-primary);
            font-weight: 600;
        }}

        .email-body-box {{
            margin-bottom: 16px;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 12px;
        }}

        .box-label {{
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 700;
            margin-bottom: 4px;
        }}

        .body-text {{
            font-size: 0.85rem;
            color: #cbd5e1;
            white-space: pre-wrap;
            line-height: 1.45;
        }}

        .details-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 12px;
        }}

        @media (max-width: 900px) {{
            .details-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .reasoning-box, .action-box {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 12px;
        }}

        .reasoning-text {{
            font-size: 0.82rem;
            color: #94a3b8;
            line-height: 1.4;
        }}

        .action-code {{
            font-family: var(--font-mono);
            font-size: 0.8rem;
            color: #38bdf8;
            font-weight: 600;
            margin-bottom: 4px;
        }}

        .action-desc {{
            font-size: 0.82rem;
            color: var(--text-secondary);
        }}

        /* Draft Box */
        .draft-box {{
            margin-top: 12px;
            background: rgba(16, 185, 129, 0.05);
            border: 1px dashed rgba(16, 185, 129, 0.3);
            border-radius: 6px;
            padding: 12px;
        }}

        .draft-title {{
            font-size: 0.78rem;
            font-weight: 700;
            color: #10b981;
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 8px;
            text-transform: uppercase;
        }}

        .draft-meta {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }}

        .draft-body {{
            font-size: 0.82rem;
            color: #a7f3d0;
            white-space: pre-wrap;
            background: rgba(0, 0, 0, 0.2);
            padding: 10px;
            border-radius: 4px;
            margin-top: 6px;
            font-family: var(--font-mono);
        }}

        /* Tables Section */
        .tables-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }}

        @media (max-width: 1100px) {{
            .tables-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .table-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.83rem;
            text-align: left;
        }}

        th {{
            background: var(--bg-input);
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.72rem;
            letter-spacing: 0.05em;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
        }}

        td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-primary);
            vertical-align: top;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .code-badge {{
            font-family: var(--font-mono);
            font-size: 0.78rem;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
        }}

        .email-id-sm {{
            font-family: var(--font-mono);
            font-size: 0.78rem;
            color: var(--text-secondary);
        }}

        .amount-val {{
            font-family: var(--font-mono);
            font-weight: 700;
            color: #34d399;
        }}

        .time-val {{
            font-size: 0.75rem;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }}

        .task-badge {{
            font-size: 0.72rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }}

        .dispute-badge {{
            color: #f87171;
            background: rgba(248, 113, 113, 0.15);
        }}

        .review-badge {{
            color: #c084fc;
            background: rgba(192, 132, 252, 0.15);
        }}

        .prio-high {{
            color: #ef4444;
        }}

        .prio-normal {{
            color: #fbbf24;
        }}

        .empty-cell {{
            text-align: center;
            color: var(--text-muted);
            padding: 20px;
        }}
    </style>
</head>
<body>

    <header>
        <div class="brand-title">
            <span class="status-dot"></span>
            <h1>AP Email Classifier Ops Console</h1>
        </div>
        <div class="header-meta">
            <div>Processed: <strong>{total_emails} Emails</strong></div>
            <div>Last Execution: <strong>{run_timestamp}</strong></div>
        </div>
    </header>

    <div class="section-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
        </svg>
        Classification Summary Metrics
    </div>

    <div class="stats-grid">
        {stat_cards_html}
    </div>

    <div class="section-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
        </svg>
        Email Processing Activity Stream ({total_emails})
    </div>

    <div class="email-cards-container">
        {email_cards_html}
    </div>

    <div class="section-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="8" y1="6" x2="21" y2="6"></line>
            <line x1="8" y1="12" x2="21" y2="12"></line>
            <line x1="8" y1="18" x2="21" y2="18"></line>
            <line x1="3" y1="6" x2="3.01" y2="6"></line>
            <line x1="3" y1="12" x2="3.01" y2="12"></line>
            <line x1="3" y1="18" x2="3.01" y2="18"></line>
        </svg>
        Ledgers & Task Escalations
    </div>

    <div class="tables-grid">
        <div class="table-card">
            <div class="section-title" style="font-size: 0.95rem; margin-bottom: 12px;">
                Accounts Payable Invoice Ledger
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Invoice ID</th>
                        <th>Email ID</th>
                        <th>From</th>
                        <th>Amount</th>
                        <th>Logged At</th>
                    </tr>
                </thead>
                <tbody>
                    {invoice_rows}
                </tbody>
            </table>
        </div>

        <div class="table-card">
            <div class="section-title" style="font-size: 0.95rem; margin-bottom: 12px;">
                Escalations & Review Queue
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Email ID</th>
                        <th>Target / Priority</th>
                        <th>Summary / Reasoning</th>
                        <th>Created At</th>
                    </tr>
                </thead>
                <tbody>
                    {task_rows}
                </tbody>
            </table>
        </div>
    </div>

</body>
</html>
"""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Successfully generated dashboard HTML at: {DASHBOARD_FILE}")


if __name__ == "__main__":
    generate_dashboard()
