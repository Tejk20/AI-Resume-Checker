import hashlib
import re
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models import User, AuthSession
from app.services.auth import COOKIE, check_origin, create_session, current_user, hash_password, throttle, user_info, verify_password

router = APIRouter(prefix='/api/v1/auth', dependencies=[Depends(check_origin)])
DB = Annotated[Session, Depends(get_db)]


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', value):
            raise ValueError('Enter a valid email address.')
        return value


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
    if not user or not valid:
        raise HTTPException(401, 'Email or password is incorrect.')
    create_session(db, user, response)
    return {'user':user_info(user)}


@router.get('/me')
def me(user=Depends(current_user)):
    return {'user':user_info(user), 'auth_required':settings.auth_required}


@router.post('/logout', status_code=204)
def logout(request: Request, response: Response, db: DB):
    token = request.cookies.get(COOKIE, '')
    db.execute(delete(AuthSession).where(AuthSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    db.commit()
    response.delete_cookie(COOKIE, path='/', secure=settings.secure_cookies, httponly=True, samesite='lax')
