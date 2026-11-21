from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock
import hashlib
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import select
from test_api import client, signup_account
from app.core.config import settings
from app.models import PasswordResetToken
from app.models.entities import now
from app.services import password_reset, workers


def configured(monkeypatch):
    monkeypatch.setattr(settings, 'brevo_api_key', SecretStr('synthetic-test-key'))
    monkeypatch.setattr(settings, 'password_reset_sender', 'recovery@example.test')
    monkeypatch.setattr(settings, 'public_origin', 'https://hirelens.example.test')
    delivery = Mock()
    monkeypatch.setattr(password_reset, 'deliver_reset_email', delivery)
    # Keep coverage for previously issued link-based recovery requests.
    monkeypatch.setattr(password_reset, 'issue_temporary_password', password_reset.issue_token)
    return delivery


def token_from(delivery):
    return parse_qs(urlsplit(delivery.call_args.args[1]).fragment)['token'][0]


def test_unconfigured_email_never_claims_a_reset_was_sent(client, monkeypatch):
    user = signup_account(client, 'no-sender')
    monkeypatch.setattr(settings, 'brevo_api_key', None)
    for email in [user['email'], 'unknown@example.test']:
        response = client.post('/api/v1/auth/forgot-password', json={'email': email})
        assert response.status_code == 503
        assert 'not configured' in response.json()['detail']


def test_reset_single_use_hash_storage_and_session_revocation(client, monkeypatch):
    delivery = configured(monkeypatch)
    user = signup_account(client, 'recovery')
    old_cookie = client.cookies.get('avom_session')
    response = client.post('/api/v1/auth/forgot-password', json={'email': user['email']})
    assert response.status_code == 202
    token = token_from(delivery)
    assert token not in response.text
    assert delivery.call_args.args[1].startswith('https://hirelens.example.test/reset-password#token=')
    with workers.SessionLocal() as db:
        row = db.scalar(select(PasswordResetToken))
        assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert row.token_hash != token
    body = {'token': token, 'password': 'New-test-passphrase-2026'}
    assert client.post('/api/v1/auth/reset-password', json=body).status_code == 200
    assert client.get('/api/v1/auth/me', headers={'Cookie': 'avom_session='+old_cookie}).json()['user'] is None
    assert client.post('/api/v1/auth/reset-password', json=body).status_code == 400
    assert client.post('/api/v1/auth/login', json={'email': user['email'], 'password': 'Fictional-Test-Passphrase-42'}).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': user['email'], 'password': body['password']}).status_code == 200


def test_unknown_accounts_have_the_same_response_and_do_not_send_mail(client, monkeypatch):
    delivery = configured(monkeypatch)
    unknown = client.post('/api/v1/auth/forgot-password', json={'email': 'unknown@example.test'})
    assert unknown.status_code == 202
    delivery.assert_not_called()
    user = signup_account(client, 'known')
    known = client.post('/api/v1/auth/forgot-password', json={'email': user['email']})
    assert unknown.json() == known.json()
    assert 'token' not in known.json()


def test_expired_and_superseded_links_fail_without_changing_password(client, monkeypatch):
    delivery = configured(monkeypatch)
    user = signup_account(client, 'expired')
    client.post('/api/v1/auth/forgot-password', json={'email': user['email']})
    old = token_from(delivery)
    client.post('/api/v1/auth/forgot-password', json={'email': user['email']})
    latest = token_from(delivery)
    assert old != latest
    assert client.post('/api/v1/auth/reset-password', json={'token': old, 'password': 'Unwanted-password-2026'}).status_code == 400
    with workers.SessionLocal() as db:
        row = db.scalar(select(PasswordResetToken))
        row.expires_at = now()-timedelta(seconds=1)
        db.commit()
    assert client.post('/api/v1/auth/reset-password', json={'token': latest, 'password': 'Unwanted-password-2026'}).status_code == 400
    assert client.post('/api/v1/auth/login', json={'email': user['email'], 'password': 'Fictional-Test-Passphrase-42'}).status_code == 200


def test_hash_failure_rolls_back_token_claim_and_allows_retry(client, monkeypatch):
    delivery = configured(monkeypatch)
    user = signup_account(client, 'retry')
    client.post('/api/v1/auth/forgot-password', json={'email': user['email']})
    token = token_from(delivery)
    from app.api import auth_routes
    real_hash = auth_routes.hash_password
    monkeypatch.setattr(auth_routes, 'hash_password', Mock(side_effect=HTTPException(503, 'Please retry.')))
    body = {'token': token, 'password': 'New-test-passphrase-2026'}
    assert client.post('/api/v1/auth/reset-password', json=body).status_code == 503
    monkeypatch.setattr(auth_routes, 'hash_password', real_hash)
    assert client.post('/api/v1/auth/reset-password', json=body).status_code == 200
