"""Email delivery for the brianborg-x review workflow — Brian's replacement for
the OnPath Slack review channel. Sends via Gmail SMTP using an app password.

Required env (add to ~/Projects/onpath-org/operations/.env yourself, never paste
a secret into chat):
  GMAIL_USER            sending account, e.g. brian@onpathtesting.com
  GMAIL_APP_PASSWORD    a Gmail app password (Google account > Security > App passwords)
  REVIEW_EMAIL_TO       (optional) where drafts go; defaults to GMAIL_USER
"""

import os
import smtplib
import ssl
from email.message import EmailMessage


class EmailNotConfigured(RuntimeError):
    pass


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise EmailNotConfigured(
            f"{key} is not set. Add it to operations/.env to enable email "
            f"delivery (see scripts/lib/email_send.py docstring). "
            f"Run with --no-email to preview without sending."
        )
    return val


def send_email(subject: str, html_body: str, text_body: str, to: str | None = None) -> str:
    """Send a multipart text+HTML email. Returns the recipient on success."""
    user = _require("GMAIL_USER")
    app_pw = _require("GMAIL_APP_PASSWORD")
    recipient = to or os.environ.get("REVIEW_EMAIL_TO") or user

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = recipient
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
        server.login(user, app_pw)
        server.send_message(msg)
    return recipient
