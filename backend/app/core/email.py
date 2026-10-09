"""Outgoing email: SMTP in production; in development messages are logged and kept in OUTBOX."""
import logging
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from html import escape

from app.core.config import settings

logger = logging.getLogger("app.email")

OUTBOX: list[dict] = []  # development/test only: the most recent messages, newest last
_OUTBOX_LIMIT = 200
_P = '<p style="margin:0 0 16px;font-size:14px;line-height:1.7;color:#3d4854;">'
_P_MUTED = '<p style="margin:0 0 12px;font-size:13px;line-height:1.7;color:#6b7681;">'


class EmailError(Exception):
    pass


def send_email(to: str, subject: str, html: str, text: str) -> None:
    """Send one message. Raises EmailError when SMTP is configured and delivery fails."""
    if not settings.smtp_host:
        OUTBOX.append({"to": to, "subject": subject, "html": html, "text": text})
        del OUTBOX[:-_OUTBOX_LIMIT]
        if settings.is_development:
            logger.info("Email (dev mode, not sent) to=%s subject=%s\n%s", to, subject, text)
        return
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = settings.mail_from, to, subject
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        logger.error("Email delivery failed to=%s subject=%s error=%s", to, subject, exc)
        raise EmailError(str(exc)) from exc


def _wrap(title: str, body_html: str) -> str:
    brand = escape(settings.app_name)
    year = datetime.now(UTC).year
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        '<body style="margin:0;padding:0;background:#f3f5f7;font-family:-apple-system,BlinkMacSystemFont,'
        "'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#0f1720;\">"
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f5f7;padding:32px 12px;">'
        '<tr><td align="center"><table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;'
        'background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(15,23,32,.08);">'
        '<tr><td style="background:linear-gradient(135deg,#0E7C4A,#084a2b);padding:28px 32px;color:#ffffff;">'
        f'<div style="font-size:22px;font-weight:800;letter-spacing:-.02em;">{brand}</div>'
        '<div style="font-size:12px;opacity:.85;margin-top:4px;">Connect. Discover. Work. Grow.</div>'
        '</td></tr><tr><td style="padding:32px;">'
        f'<h1 style="font-size:20px;font-weight:700;margin:0 0 16px;color:#0f1720;">{escape(title)}</h1>'
        f"{body_html}</td></tr>"
        '<tr><td style="padding:20px 32px;background:#f8fafb;border-top:1px solid #e4e7eb;font-size:11.5px;'
        'color:#6b7681;line-height:1.6;">'
        f"You are receiving this email because you have an account on {brand}. "
        "If you did not request this, you can safely ignore this email."
        f"<br>&copy; {year} {brand}. Koforidua, Eastern Region, Ghana."
        "</td></tr></table></td></tr></table></body></html>"
    )


def _code_box(label: str, code: str, minutes: int) -> str:
    spaced = escape(" ".join(code))
    return (
        '<div style="background:#e8f5ee;border:1px solid #d0ebd9;border-radius:12px;padding:24px;'
        'text-align:center;margin:0 0 20px;">'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:.14em;color:#0a5f38;margin-bottom:10px;">{label}</div>'
        '<div style="font-size:34px;font-weight:800;letter-spacing:.32em;color:#0E7C4A;font-family:monospace;">'
        f"{spaced}</div>"
        f'<div style="font-size:12px;color:#6b7681;margin-top:10px;">This code expires in {minutes} minutes</div>'
        "</div>"
    )


def send_verification_code(to: str, first_name: str, code: str, minutes: int) -> None:
    app = escape(settings.app_name)
    subject = f"Verify your {settings.app_name} email"
    body = (
        f"{_P}Hi {escape(first_name)},</p>"
        f"{_P}Welcome to {app}! Use the verification code below to confirm your email address.</p>"
        f"{_code_box('VERIFICATION CODE', code, minutes)}"
        f"{_P_MUTED}For your security: never share this code with anyone. {app} staff will never ask "
        "you for your verification code.</p>"
        f"{_P_MUTED}If you did not create this account, you can ignore this email.</p>"
    )
    text = f"Hi {first_name},\n\nYour {settings.app_name} verification code is {code}. It expires in {minutes} minutes."
    send_email(to, subject, _wrap(subject, body), text)


def send_password_reset_code(to: str, first_name: str, code: str, minutes: int) -> None:
    subject = f"Reset your {settings.app_name} password"
    body = (
        f"{_P}Hi {escape(first_name)},</p>"
        f"{_P}We received a request to reset your password. Enter this code to choose a new one.</p>"
        f"{_code_box('PASSWORD RESET CODE', code, minutes)}"
        f"{_P_MUTED}If you did not request a reset, ignore this email. Your password has not been changed.</p>"
    )
    text = f"Hi {first_name},\n\nYour {settings.app_name} password reset code is {code}. It expires in {minutes} minutes."
    send_email(to, subject, _wrap(subject, body), text)


def send_welcome(to: str, first_name: str) -> None:
    app = escape(settings.app_name)
    subject = f"Welcome to {settings.app_name}"
    body = (
        f"{_P}Hi {escape(first_name)},</p>"
        f"{_P}Your email is verified. Welcome to <b>{app}</b> — the professional network for Koforidua and beyond.</p>"
        '<ul style="padding-left:18px;margin:0 0 20px;font-size:14px;line-height:1.9;color:#3d4854;">'
        "<li>Complete your profile to get discovered</li>"
        "<li>Connect with professionals and employers</li>"
        "<li>Discover local jobs, companies and events</li></ul>"
        f"{_P}We are glad to have you on board.</p>"
    )
    send_email(to, subject, _wrap(subject, body), f"Hi {first_name},\n\nYour email is verified. Welcome to {settings.app_name}!")


def send_verification_decision(to: str, first_name: str, approved: bool, what: str, reason: str = "") -> None:
    """Outcome of a verified-badge request; `what` is e.g. 'profile' or 'company page for Acme'."""
    app = escape(settings.app_name)
    if approved:
        subject = f"Your {settings.app_name} verification was approved"
        body = (
            f"{_P}Hi {escape(first_name)},</p>"
            f"{_P}Good news — your {escape(what)} on <b>{app}</b> has been approved. Your verified badge is now active.</p>"
            f"{_P}Thank you for helping keep {app} trustworthy.</p>"
        )
        text = f"Hi {first_name},\n\nYour {what} on {settings.app_name} has been approved."
    else:
        subject = f"Update regarding your {settings.app_name} verification"
        reason_html = (
            '<div style="background:#fee2e2;border:1px solid #fecaca;border-radius:10px;padding:14px 16px;'
            f'margin:0 0 18px;font-size:13px;line-height:1.6;color:#991b1b;"><b>Reason:</b> {escape(reason)}</div>'
            if reason
            else ""
        )
        body = (
            f"{_P}Hi {escape(first_name)},</p>"
            f"{_P}After reviewing your verification request for your {escape(what)}, our team was unable to "
            "approve it at this time.</p>"
            f"{reason_html}{_P}You may update your information and submit a new request at any time.</p>"
            f"{_P}— The {app} team</p>"
        )
        text = f"Hi {first_name},\n\nYour verification request for your {what} was not approved. {reason}".strip()
    send_email(to, subject, _wrap(subject, body), text)


def send_new_application(to: str, applicant_name: str, job_title: str) -> None:
    subject = f"New application for {job_title}"
    body = (
        f"{_P}<b>{escape(applicant_name)}</b> applied for <b>{escape(job_title)}</b>.</p>"
        f"{_P}Open {escape(settings.app_name)} to review the application.</p>"
    )
    send_email(to, subject, _wrap(subject, body), f"{applicant_name} applied for {job_title}.")
