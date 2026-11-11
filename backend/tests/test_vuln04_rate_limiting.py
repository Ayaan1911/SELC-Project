"""Regression test for VULN-04 (no rate limiting / lockout on login).

Replays the exploit from docs/VULNERABILITIES.md: hammering /api/login with
wrong passwords. It must now be throttled with a temporary lockout.
"""
import app as app_module


def test_repeated_failures_trigger_lockout(client, seeded):
    # Exactly MAX_LOGIN_ATTEMPTS wrong attempts (same as the exploit replay).
    codes = []
    for _ in range(app_module.MAX_LOGIN_ATTEMPTS):
        resp = client.post("/api/login", json={"username": "alice", "password": "wrong"})
        codes.append(resp.status_code)
    assert codes == [401] * app_module.MAX_LOGIN_ATTEMPTS

    # The next attempt - even with the CORRECT password - must be locked out.
    resp = client.post("/api/login", json={"username": "alice", "password": "alice123"})
    assert resp.status_code == 429


def test_lockout_clears_after_the_window(client, seeded, monkeypatch):
    monkeypatch.setattr(app_module, "LOGIN_LOCKOUT_SECONDS", 0)  # expire immediately

    for _ in range(app_module.MAX_LOGIN_ATTEMPTS):
        client.post("/api/login", json={"username": "bob", "password": "wrong"})

    resp = client.post("/api/login", json={"username": "bob", "password": "bob123"})
    assert resp.status_code == 200  # lockout window already passed


def test_other_accounts_are_not_affected(client, seeded):
    for _ in range(app_module.MAX_LOGIN_ATTEMPTS):
        client.post("/api/login", json={"username": "alice", "password": "wrong"})

    # bob's account must still be usable - the lockout is per-username.
    resp = client.post("/api/login", json={"username": "bob", "password": "bob123"})
    assert resp.status_code == 200
