"""Regression test for VULN-02 (IDOR on GET /api/orders/{id}).

Replays the exploit from docs/VULNERABILITIES.md: alice tries to read bob's
order by changing the ID. It must now be rejected.
"""
from tests.helpers import auth_headers, login


def test_user_cannot_read_another_users_order(client, seeded):
    alice_token = login(client, "alice", "alice123")

    resp = client.get(f"/api/orders/{seeded['order_bob']}", headers=auth_headers(alice_token))

    assert resp.status_code == 404


def test_user_can_still_read_their_own_order(client, seeded):
    alice_token = login(client, "alice", "alice123")

    resp = client.get(f"/api/orders/{seeded['order_alice']}", headers=auth_headers(alice_token))

    assert resp.status_code == 200
    assert resp.json()["id"] == seeded["order_alice"]


def test_admin_can_still_read_any_order(client, seeded):
    admin_token = login(client, "admin", "admin123")

    resp = client.get(f"/api/orders/{seeded['order_bob']}", headers=auth_headers(admin_token))

    assert resp.status_code == 200
    assert resp.json()["id"] == seeded["order_bob"]


def test_nonexistent_order_is_also_404(client, seeded):
    alice_token = login(client, "alice", "alice123")

    resp = client.get("/api/orders/999999", headers=auth_headers(alice_token))

    assert resp.status_code == 404
