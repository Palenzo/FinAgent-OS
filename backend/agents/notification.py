"""
Agent 8 — Notification Agent
Sends emails via SendGrid on report completion or critical anomaly.
"""

import logging
import os
from typing import Optional

import sendgrid
from sendgrid.helpers.mail import Mail

logger = logging.getLogger("agent.notification")

FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "reports@finagent.io")
ALERT_RECIPIENT = os.getenv("ALERT_EMAIL_RECIPIENT", "team@finagent.io")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")


def _get_sg_client():
    if not SENDGRID_API_KEY:
        raise RuntimeError("SENDGRID_API_KEY not configured")
    return sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)


def _build_report_email(state: dict) -> Mail:
    report = state.get("report_result", {})
    markdown = report.get("markdown_report", "Report unavailable")
    run_id = state.get("run_id", "unknown")

    html_body = f"""
    <html><body>
    <h2>FinAgent OS — Financial Report Ready</h2>
    <p>Pipeline run <strong>{run_id}</strong> completed successfully.</p>
    <hr>
    <pre style="font-family: monospace; white-space: pre-wrap;">{markdown[:3000]}</pre>
    <p><em>Full report available in the FinAgent OS dashboard.</em></p>
    </body></html>
    """

    return Mail(
        from_email=FROM_EMAIL,
        to_emails=ALERT_RECIPIENT,
        subject=f"FinAgent OS — Report Ready (Run {run_id[:8]})",
        html_content=html_body,
    )


def _build_anomaly_alert_email(state: dict) -> Mail:
    anomaly = state.get("anomaly_result", {})
    critical = anomaly.get("critical_count", 0)
    items = anomaly.get("anomalies", [])
    run_id = state.get("run_id", "unknown")

    rows = "".join(
        f"<tr><td>{a.get('description','—')}</td><td>${a.get('amount',0):,.2f}</td>"
        f"<td style='color:red'>{a.get('severity','?').upper()}</td>"
        f"<td>{a.get('reason','—')}</td></tr>"
        for a in items
        if a.get("severity") in ("high", "critical")
    )

    html_body = f"""
    <html><body>
    <h2 style="color:red;">⚠️ FinAgent OS — Critical Anomaly Alert</h2>
    <p>Run <strong>{run_id}</strong> flagged <strong>{critical} critical anomalies</strong>.</p>
    <table border="1" cellpadding="6">
      <tr><th>Description</th><th>Amount</th><th>Severity</th><th>Reason</th></tr>
      {rows}
    </table>
    <p><em>Review in the FinAgent OS dashboard immediately.</em></p>
    </body></html>
    """

    return Mail(
        from_email=FROM_EMAIL,
        to_emails=ALERT_RECIPIENT,
        subject=f"🚨 CRITICAL: {critical} Anomalies Detected — FinAgent OS",
        html_content=html_body,
    )


async def send_notifications(state: dict):
    """
    Determines which emails to send based on pipeline outcome.
    Gracefully skips if SendGrid is not configured (dev environment).
    """
    if not SENDGRID_API_KEY:
        logger.warning("[NotificationAgent] SendGrid not configured — skipping email")
        return

    sg = _get_sg_client()
    anomaly = state.get("anomaly_result", {})
    critical_count = anomaly.get("critical_count", 0)

    emails_sent = []

    # Always send report email on completion
    if state.get("status") == "completed" and state.get("report_result"):
        try:
            msg = _build_report_email(state)
            response = sg.send(msg)
            logger.info(
                "[NotificationAgent] Report email sent, status=%d", response.status_code
            )
            emails_sent.append("report")
        except Exception as exc:
            logger.error("[NotificationAgent] Report email failed: %s", exc)

    # Send anomaly alert if any critical issues found
    if critical_count > 0:
        try:
            msg = _build_anomaly_alert_email(state)
            response = sg.send(msg)
            logger.info(
                "[NotificationAgent] Anomaly alert sent, status=%d", response.status_code
            )
            emails_sent.append("anomaly_alert")
        except Exception as exc:
            logger.error("[NotificationAgent] Anomaly alert failed: %s", exc)

    logger.info("[NotificationAgent] Emails sent: %s", emails_sent)
