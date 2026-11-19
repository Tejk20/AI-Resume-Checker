"""Password hashing and revocable, database-backed browser sessions."""
from collections import defaultdict, deque
from datetime import timedelta, timezone
import hashlib
import hmac
import secrets
import os
from threading import Lock, BoundedSemaphore
import time
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select, or_
from app.core.config import settings
from app.core.database import get_db
from app.models import AuthSession, User, Job
from app.models.entities import now

COOKIE = 'avom_session'
HASH_SLOTS = BoundedSemaphore(2)
ATTEMPTS = defaultdict(deque)
ATTEMPT_LOCK = Lock()


def throttle(request, email):
    # Per-process guard, appropriate to the single-process deployment. No raw
    # passwords or emails are kept in counters. Restart resets the window.
    stamp = time.monotonic()
    keys = [('ip', request.client.host if request.client else 'unknown'),
            ('email', hashlib.sha256(email.encode()).hexdigest())]
    with ATTEMPT_LOCK:
        for key in list(ATTEMPTS):
            while ATTEMPTS[key] and ATTEMPTS[key][0] < stamp-900:
                ATTEMPTS[key].popleft()
            if not ATTEMPTS[key]:
                del ATTEMPTS[key]
        if any(len(ATTEMPTS[key]) >= (60 if key[0] == 'ip' else 10) for key in keys):
            raise HTTPException(429, 'Too many attempts. Try again in 15 minutes.', headers={'Retry-After':'900'})
        for key in keys:
            ATTEMPTS[key].append(stamp)


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    if not HASH_SLOTS.acquire(blocking=False):
        raise HTTPException(503, 'Account service is busy. Please retry shortly.')
    try:
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()
    finally:
        HASH_SLOTS.release()
    return f'pbkdf2_sha256$600000${salt}${digest}'


def verify_password(password, stored):
    try:
        _, _, salt, _ = stored.split('$')
        return hmac.compare_digest(hash_password(password, salt), stored)
    except ValueError:
        return False


def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if not token or len(token) > 200:
        return None
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    if not session:
        return None
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return db.get(User, session.user_id) if expires > now() else None


def visible_jobs(user):
    if user:
        return or_(Job.is_demo.is_(True), Job.owner_id == user.id)
    if settings.auth_required:
        return Job.is_demo.is_(True)
    return Job.owner_id.is_(None)


def check_origin(request: Request):
    if request.method not in {'POST', 'PATCH', 'PUT', 'DELETE'}:
        return
    origin = request.headers.get('origin')
    allowed = {str(request.base_url).rstrip('/'), settings.public_origin.rstrip('/'),
               os.getenv('RENDER_EXTERNAL_URL', '').rstrip('/'), *settings.cors_origins}
    if origin and origin.rstrip('/') not in allowed:
        raise HTTPException(403, 'This request origin is not allowed.')


def create_session(db, user, response):
    from sqlalchemy import delete
    db.execute(delete(AuthSession).where(AuthSession.expires_at < now()))
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                       expires_at=now()+timedelta(days=7)))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=7*86400, httponly=True,
                        secure=settings.secure_cookies, samesite='lax', path='/')


def user_info(user):
    return {'id':str(user.id), 'name':user.name, 'email':user.email} if user else None
