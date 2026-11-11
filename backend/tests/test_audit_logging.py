"""Tests for security audit logging (step 8): failed logins, lockouts,
admin actions and authorization failures are recorded in the audit_log table.
"""
import database
from tests.helpers import auth_headers, login


def _audit_rows(event_type=None):
    conn = database.get_db()
    if event_type:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE event_type = ? ORDER BY id", (event_type,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def test_failed_login_is_logged(client, seeded):
    client.post("/api/login", json={"username": "alice", "password": "wrong"})

    rows = _audit_rows("login_failed")
    assert len(rows) == 1
    assert rows[0]["username"] == "alice"


def test_lockout_is_logged(client, seeded):
    import app as app_module

    for _ in range(app_module.MAX_LOGIN_ATTEMPTS):
        client.post("/api/login", json={"username": "bob", "password": "wrong"})
    client.post("/api/login", json={"username": "bob", "password": "bob123"})  # now locked out

    rows = _audit_rows("login_lockout")
    assert len(rows) == 1
    assert rows[0]["username"] == "bob"


def test_admin_action_is_logged(client, seeded):
    admin_token = login(client, "admin", "admin123")

    client.post(
        "/api/admin/products",
        json={"name": "Gizmo", "description": "", "price": 5, "stock": 1},
        headers=auth_headers(admin_token),
    )

    rows = _audit_rows("admin_action")
    assert any("Gizmo" in r["detail"] for r in rows)
    assert rows[-1]["username"] == "admin"


def test_non_admin_admin_attempt_is_logged_as_authz_denied(client, seeded):
    bob_token = login(client, "bob", "bob123")

    client.post(
        "/api/admin/products",
        json={"name": "x", "description": "", "price": 1, "stock": 1},
        headers=auth_headers(bob_token),
    )

    rows = _audit_rows("authz_denied")
    assert len(rows) == 1
    assert rows[0]["username"] == "bob"


def test_idor_attempt_is_logged_as_authz_denied(client, seeded):
    alice_token = login(client, "alice", "alice123")

    client.get(f"/api/orders/{seeded['order_bob']}", headers=auth_headers(alice_token))

    rows = _audit_rows("authz_denied")
    assert any("alice" == r["username"] and f"#{seeded['order_bob']}" in r["detail"] for r in rows)
