"""
Transactional email via Resend (verification, reset password, welcome).
Set RESEND_API_KEY, EMAIL_FROM, and optionally EMAIL_REPLY_TO and FRONTEND_URL in .env.
"""
from typing import Optional
import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(
    to: str | list[str],
    subject: str,
    html: str,
    reply_to: Optional[str] = None,
) -> bool:
    """
    Send a single email via Resend.
    Returns True if sent, False if Resend not configured or send failed.
    """
    settings = get_settings()
    if not settings.resend_api_key or not settings.email_from:
        logger.warning("email_skipped_resend_not_configured", to=to, subject=subject)
        return False

    recipients = [to] if isinstance(to, str) else to
    payload = {
        "from": settings.email_from,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if reply_to or settings.email_reply_to:
        payload["reply_to"] = reply_to or settings.email_reply_to

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                RESEND_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                timeout=10.0,
            )
        if r.status_code != 200 and r.status_code != 201:
            logger.error(
                "resend_send_failed",
                status=r.status_code,
                body=r.text[:500],
                to=recipients,
                subject=subject,
            )
            return False
        logger.info("email_sent", to=recipients, subject=subject)
        return True
    except Exception as e:
        logger.exception("email_send_error", error=str(e), to=recipients, subject=subject)
        return False


def verification_email_html(frontend_url: str, token: str, email: str) -> str:
    """HTML body for email verification link."""
    link = f"{frontend_url.rstrip('/')}/verify-email?token={token}"
    return f"""
    <p>Hi,</p>
    <p>Please verify your email by clicking the link below:</p>
    <p><a href="{link}">Verify email</a></p>
    <p>If you didn't create an account, you can ignore this email.</p>
    <p>— UnSearch</p>
    """


def reset_password_email_html(frontend_url: str, token: str) -> str:
    """HTML body for password reset link."""
    link = f"{frontend_url.rstrip('/')}/reset-password?token={token}"
    return f"""
    <p>Hi,</p>
    <p>You requested a password reset. Click the link below to set a new password:</p>
    <p><a href="{link}">Reset password</a></p>
    <p>This link expires in 1 hour. If you didn't request this, ignore this email.</p>
    <p>— UnSearch</p>
    """


def welcome_email_html(frontend_url: str, name: Optional[str] = None) -> str:
    """HTML body for welcome email after signup."""
    dashboard_url = f"{frontend_url.rstrip('/')}/dashboard"
    greeting = f"Hi {name}," if name else "Hi,"
    return f"""
    <p>{greeting}</p>
    <p>Welcome to UnSearch. Your account is ready.</p>
    <p><a href="{dashboard_url}">Go to Dashboard</a></p>
    <p>— UnSearch</p>
    """


async def send_verification_email(to: str, token: str) -> bool:
    """Send email verification link."""
    settings = get_settings()
    return await send_email(
        to=to,
        subject="Verify your UnSearch email",
        html=verification_email_html(settings.frontend_url, token, to),
    )


async def send_reset_password_email(to: str, token: str) -> bool:
    """Send password reset link."""
    settings = get_settings()
    return await send_email(
        to=to,
        subject="Reset your UnSearch password",
        html=reset_password_email_html(settings.frontend_url, token),
    )


async def send_welcome_email(to: str, name: Optional[str] = None) -> bool:
    """Send welcome email after registration."""
    settings = get_settings()
    return await send_email(
        to=to,
        subject="Welcome to UnSearch",
        html=welcome_email_html(settings.frontend_url, name),
    )
