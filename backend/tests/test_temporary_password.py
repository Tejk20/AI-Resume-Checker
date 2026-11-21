from datetime import timedelta
from unittest.mock import Mock
from pydantic import SecretStr
from sqlalchemy import select
from test_api import client, signup_account
from app.core.config import settings
from app.models import PasswordResetToken
from app.models.entities import now
from app.services import password_reset, workers
from app.services.auth import verify_password

OLD = 'Fictional-Test-Passphrase-42'
NEW = 'New-test-passphrase-2026'


def configured(monkeypatch):
    monkeypatch.setattr(settings, 'brevo_api_key', SecretStr('synthetic-test-key'))
    monkeypatch.setattr(settings, 'password_reset_sender', 'recovery@example.test')
    monkeypatch.setattr(settings, 'public_origin', 'https://hirelens.example.test')
    delivery = Mock()
    monkeypatch.setattr(password_reset, 'deliver_reset_email', delivery)
    return delivery


def login(client, user, password):
    return client.post('/api/v1/auth/login', json={'email': user['email'], 'password': password})


def request_password(client, user, delivery):
    result = client.post('/api/v1/auth/forgot-password', json={'email': user['email']})
    assert result.status_code == 202
    password = delivery.call_args.args[1]
    assert password not in result.text
    return password


def test_temporary_password_is_hashed_and_optional_to_change(client, monkeypatch):
    delivery = configured(monkeypatch)
    user = signup_account(client, 'temporary')
    old_cookie = client.cookies.get('avom_session')
    password = request_password(client, user, delivery)
    with workers.SessionLocal() as db:
        row = db.scalar(select(PasswordResetToken))
        assert password not in row.temporary_password_hash
        assert verify_password(password, row.temporary_password_hash)
    assert login(client, user, OLD).status_code == 200
    assert login(client, user, password).status_code == 200
    assert client.get('/api/v1/auth/me', headers={'Cookie': 'avom_session='+old_cookie}).json()['user'] is None
    assert login(client, user, OLD).status_code == 401
    assert login(client, user, password).status_code == 200
    response = client.post('/api/v1/auth/change-password', json={'current_password': password, 'new_password': NEW})
    assert response.status_code == 200
    assert client.get('/api/v1/auth/me').json()['user']['id'] == user['id']
    assert login(client, user, password).status_code == 401
    assert login(client, user, NEW).status_code == 200


def test_superseded_and_expired_passwords_keep_existing_password(client, monkeypatch):
    delivery = configured(monkeypatch)
    user = signup_account(client, 'expired')
    first = request_password(client, user, delivery)
    latest = request_password(client, user, delivery)
    assert first != latest
    assert login(client, user, first).status_code == 401
    with workers.SessionLocal() as db:
        row = db.scalar(select(PasswordResetToken))
        row.expires_at = now()-timedelta(seconds=1)
        db.commit()
    assert login(client, user, latest).status_code == 401
    assert login(client, user, OLD).status_code == 200


def test_profile_requires_login_and_current_password(client, monkeypatch):
    body = {'current_password': OLD, 'new_password': NEW}
    assert client.post('/api/v1/auth/change-password', json=body).status_code == 401
    delivery = configured(monkeypatch)
    user = signup_account(client, 'profile')
    temporary = request_password(client, user, delivery)
    assert client.post('/api/v1/auth/change-password', json={**body, 'current_password': NEW}).status_code == 400
    assert client.post('/api/v1/auth/change-password', json={'current_password': OLD, 'new_password': OLD}).status_code == 400
    assert client.post('/api/v1/auth/change-password', json=body).status_code == 200
    assert login(client, user, temporary).status_code == 401
    assert login(client, user, OLD).status_code == 401
    assert login(client, user, NEW).status_code == 200
