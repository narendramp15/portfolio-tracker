"""Email service for transactional emails (password reset, etc.).

Supports two backends:
1. SMTP (free — works with Gmail, Zoho, any SMTP provider)
2. Console fallback (development — prints to log instead of sending)

Configuration via environment variables:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your@gmail.com
    SMTP_PASSWORD=app-password-here
    SMTP_FROM=noreply@quantleap.in
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@quantleap.in")


def _smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email. Returns True on success."""
    if not _smtp_configured():
        logger.warning(
            "SMTP not configured — email NOT sent. Set SMTP_HOST, SMTP_USER, "
            "SMTP_PASSWORD env vars. Falling back to console log."
        )
        logger.info("EMAIL TO: %s | SUBJECT: %s", to, subject)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to], msg.as_string())
        logger.info("Email sent to %s (subject: %s)", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def send_password_reset_email(to: str, token: str, frontend_url: str) -> bool:
    """Send a password-reset email with a tokenized link."""
    reset_link = f"{frontend_url}/reset-password?token={token}"
    html = f"""\
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
  <h2 style="color:#4f46e5">QuantLeap — Password Reset</h2>
  <p>You requested a password reset. Click the button below to choose a new password.
     This link expires in <strong>1 hour</strong>.</p>
  <a href="{reset_link}"
     style="display:inline-block;padding:12px 24px;background:#4f46e5;color:#fff;
            text-decoration:none;border-radius:8px;font-weight:600;margin:16px 0">
    Reset Password
  </a>
  <p style="font-size:12px;color:#888">
    If you didn't request this, you can safely ignore this email.<br>
    Link: {reset_link}
  </p>
</div>"""
    return send_email(to, "Reset your QuantLeap password", html)
