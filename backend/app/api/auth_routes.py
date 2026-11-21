import hashlib
import re
from typing import Annotated
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models import User, AuthSession, PasswordResetToken
from app.models.entities import now
from app.services.auth import COOKIE, check_origin, create_session, current_user, hash_password, throttle, user_info, verify_password
from app.services import password_reset

router = APIRouter(prefix='/api/v1/auth', dependencies=[Depends(check_origin)])
DB = Annotated[Session, Depends(get_db)]


class EmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', value):
            raise ValueError('Enter a valid email address.')
        return value


class Credentials(EmailRequest):
    password: str = Field(min_length=10, max_length=128)


class ResetPassword(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=10, max_length=128)


class ChangePassword(BaseModel):
    current_password: str = Field(min_length=10, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class Signup(Credentials):
    name: str = Field(min_length=2, max_length=100)

    @field_validator('name')
    @classmethod
    def valid_name(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError('Enter your full name.')
        return value


@router.post('/signup', status_code=201)
def signup(payload: Signup, request: Request, response: Response, db: DB):
    throttle(request, payload.email)
    if db.scalar(select(User.id).where(User.email == payload.email)):
        raise HTTPException(409, 'An account with this email already exists. Sign in instead.')
    user = User(name=payload.name, email=payload.email, password_hash=hash_password(payload.password))
    try:
        db.add(user); db.flush()
        create_session(db, user, response)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'An account with this email already exists. Sign in instead.')
    return {'user':user_info(user)}


@router.post('/login')
def login(payload: Credentials, request: Request, response: Response, db: DB):
    throttle(request, payload.email)
    user = db.scalar(select(User).where(User.email == payload.email))
    # Run the same expensive hash path even for unknown accounts.
    stored = user.password_hash if user else 'pbkdf2_sha256$600000$'+'0'*32+'$'+'0'*64
    valid = verify_password(payload.password, stored)
    pending = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.consumed_at.is_(None),
        PasswordResetToken.expires_at > now(),
        PasswordResetToken.temporary_password_hash.is_not(None)
    ).order_by(PasswordResetToken.created_at.desc())) if user and not valid else None
    if pending and verify_password(payload.password, pending.temporary_password_hash):
        claimed = db.scalar(update(PasswordResetToken).where(
            PasswordResetToken.id == pending.id,
            PasswordResetToken.consumed_at.is_(None),
            PasswordResetToken.expires_at > now()
        ).values(consumed_at=now()).returning(PasswordResetToken.user_id)
          .execution_options(synchronize_session='fetch'))
        if claimed:
            user.password_hash = pending.temporary_password_hash
            db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
            db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
            valid = True
    if not user or not valid:
        raise HTTPException(401, 'Email or password is incorrect.')
    create_session(db, user, response)
    return {'user':user_info(user)}


@router.get('/me')
def me(user=Depends(current_user)):
    return {'user':user_info(user), 'auth_required':settings.auth_required}


@router.post('/forgot-password', status_code=202)
def forgot_password(payload: EmailRequest, request: Request, tasks: BackgroundTasks, response: Response, db: DB):
    throttle(request, 'reset:'+payload.email)
    response.headers['Cache-Control'] = 'no-store'
    # Fail the same way for every address until delivery is configured.
    if not password_reset.delivery_available():
        raise HTTPException(503, 'Password-reset email is not configured yet. Please contact the app administrator.')
    user = db.scalar(select(User).where(User.email == payload.email))
    if user:
        temporary = password_reset.issue_temporary_password(db, user)
        tasks.add_task(password_reset.deliver_reset_email, user.email, temporary)
    return {'message': password_reset.RESET_MESSAGE}


@router.post('/change-password')
def change_password(payload: ChangePassword, request: Request, response: Response, db: DB,
                    user=Depends(current_user)):
    if not user:
        raise HTTPException(401, 'Sign in to update your password.')
    throttle(request, 'change:'+user.email)
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, 'Your current password is incorrect.')
    if payload.current_password == payload.new_password:
        raise HTTPException(400, 'Choose a different new password.')
    user.password_hash = hash_password(payload.new_password)
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
    create_session(db, user, response)
    response.headers['Cache-Control'] = 'no-store'
    return {'message': 'Password updated. Other devices have been signed out.'}


@router.post('/reset-password')
def reset_password(payload: ResetPassword, request: Request, response: Response, db: DB):
    throttle(request, 'reset-token:'+hashlib.sha256(payload.token.encode()).hexdigest())
    digest = hashlib.sha256(payload.token.encode()).hexdigest()
    try:
        # A conditional UPDATE atomically claims the token, even across requests.
        uid = db.scalar(update(PasswordResetToken).where(
            PasswordResetToken.token_hash == digest,
            PasswordResetToken.consumed_at.is_(None), PasswordResetToken.expires_at > now()
        ).values(consumed_at=now()).returning(PasswordResetToken.user_id))
        if uid is None:
            raise HTTPException(400, 'This reset link is invalid or has expired. Request a new link.')
        user = db.get(User, uid)
        user.password_hash = hash_password(payload.password)
        db.execute(delete(AuthSession).where(AuthSession.user_id == uid))
        db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == uid,
                                                  PasswordResetToken.token_hash != digest))
        db.commit()
    except Exception:
        db.rollback()
        raise
    response.delete_cookie(COOKIE, path='/', secure=settings.secure_cookies, httponly=True, samesite='lax')
    response.headers['Cache-Control'] = 'no-store'
    return {'message': 'Password updated. Sign in with your new password.'}


@router.post('/logout', status_code=204)
def logout(request: Request, response: Response, db: DB):
    token = request.cookies.get(COOKIE, '')
    db.execute(delete(AuthSession).where(AuthSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    db.commit()
    response.delete_cookie(COOKIE, path='/', secure=settings.secure_cookies, httponly=True, samesite='lax')
