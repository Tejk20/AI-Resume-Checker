"""Password recovery delivery through an HTTPS transactional email API.

Raw tokens appear only in the recipient's link, never in API responses, logs,
database rows, or URL query strings sent to the application server.
"""
from datetime import timedelta
import hashlib
import logging
import os
import secrets
from urllib.parse import urlsplit
import httpx
from app.core.config import settings
from app.models import PasswordResetToken
from app.models.entities import now

RESET_MINUTES = 30
RESET_MESSAGE = 'If an account matches that email, a password-reset link will be sent. Please check your inbox and spam folder.'


def reset_origin():
    origin = (settings.public_origin or os.getenv('RENDER_EXTERNAL_URL', '')).rstrip('/')
    parsed = urlsplit(origin)
    local = parsed.hostname in {'localhost', '127.0.0.1'}
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and local):
        return ''
    if not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return ''
    return origin


def delivery_available():
    return bool(settings.brevo_api_key and settings.brevo_api_key.get_secret_value()
                and settings.password_reset_sender and reset_origin())


def issue_token(db, user):
    from sqlalchemy import delete
    # Only the latest requested link remains valid for this account.
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.expires_at < now()))
    token = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(user_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=now()+timedelta(minutes=RESET_MINUTES)))
    db.commit()
    # Fragments are not transmitted in HTTP requests or referrer headers.
    return reset_origin() + '/reset-password#token=' + token


def deliver_reset_email(recipient, reset_url):
    try:
        response = httpx.post('https://api.brevo.com/v3/smtp/email',
            headers={'api-key': settings.brevo_api_key.get_secret_value()},
            json={'sender': {'name': 'HireLens AI', 'email': settings.password_reset_sender},
                  'to': [{'email': recipient}],
                  'subject': 'Reset your HireLens AI password',
                  'textContent': 'A password reset was requested for your HireLens AI account.\n\n'
                      + reset_url + f'\n\nThis link expires in {RESET_MINUTES} minutes and can be used once. '
                      'If you did not request this, you can ignore this email.'}, timeout=15)
        response.raise_for_status()
    except Exception as exc:
        # Provider error bodies/URLs may contain sensitive values; do not log them.
        logging.error('Password-reset email delivery failed (%s). Check email-provider configuration.', type(exc).__name__)
