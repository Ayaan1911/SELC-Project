"""Regression tests for VULN-05 (hardcoded JWT secret) and VULN-06 (tokens
that never expire).

Replays the exploits from docs/VULNERABILITIES.md: forging a token with the
old hardcoded secret, and checking a freshly issued token for an expiry claim.
"""
import time

import jwt as pyjwt  # PyJWT, only used here to decode/forge tokens for testing
import pytest

import auth
from tests.helpers import auth_headers, login


def test_old_hardcoded_secret_no_longer_signs_valid_tokens(client, seeded):
    forged = pyjwt.encode(
        {"sub": str(seeded["admin_id"]), "username": "admin", "role": "admin"},
        "securecart-secret-key-123",  # the secret that was hardcoded in v1
        algorithm="HS256",
    )

    resp = client.get(f"/api/orders/{seeded['order_bob']}", headers=auth_headers(forged))

    assert resp.status_code == 401


def test_secret_is_not_the_old_hardcoded_value():
    assert auth.SECRET_KEY != "securecart-secret-key-123"


def test_app_refuses_to_start_without_the_secret(monkeypatch):
    """Importing auth.py with no SECURECART_JWT_SECRET set must fail fast."""
    import importlib
    import os

    monkeypatch.delenv("SECURECART_JWT_SECRET", raising=False)
    # Make sure no backend/.env on disk can supply it for this check either.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)

    with pytest.raises(RuntimeError):
        importlib.reload(auth)

    # Restore the real module state for every other test in the suite.
    os.environ.setdefault("SECURECART_JWT_SECRET", "test-secret-for-ci-only-do-not-use")
    importlib.reload(auth)


def test_token_has_a_short_expiry_claim(client, seeded):
    token = login(client, "alice", "alice123")
    payload = pyjwt.decode(token, options={"verify_signature": False})

    assert "exp" in payload
    assert 0 < payload["exp"] - time.time() <= auth.TOKEN_LIFETIME_SECONDS


def test_expired_token_is_rejected(client, seeded, monkeypatch):
    monkeypatch.setattr(auth, "TOKEN_LIFETIME_SECONDS", -1)  # issue already-expired tokens
    token = login(client, "alice", "alice123")

    resp = client.get(f"/api/orders/{seeded['order_alice']}", headers=auth_headers(token))

    assert resp.status_code == 401
