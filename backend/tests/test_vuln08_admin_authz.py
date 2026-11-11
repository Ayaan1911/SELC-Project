"""Regression test for VULN-08 (missing authorization on admin endpoints).

Replays the exploit from docs/VULNERABILITIES.md: a regular user calling
POST/PUT/DELETE /api/admin/products directly. All must now be rejected.
"""
from tests.helpers import auth_headers, login

NEW_PRODUCT = {"name": "Hacked Product", "description": "added by non-admin", "price": 1, "stock": 1}


def test_non_admin_cannot_add_product(client, seeded):
    bob_token = login(client, "bob", "bob123")

    resp = client.post("/api/admin/products", json=NEW_PRODUCT, headers=auth_headers(bob_token))

    assert resp.status_code == 403


def test_non_admin_cannot_edit_product(client, seeded):
    bob_token = login(client, "bob", "bob123")

    resp = client.put(
        f"/api/admin/products/{seeded['product1']}", json=NEW_PRODUCT, headers=auth_headers(bob_token)
    )

    assert resp.status_code == 403


def test_non_admin_cannot_delete_product(client, seeded):
    bob_token = login(client, "bob", "bob123")

    resp = client.delete(f"/api/admin/products/{seeded['product1']}", headers=auth_headers(bob_token))

    assert resp.status_code == 403
    # and the product must still exist
    assert client.get(f"/api/products/{seeded['product1']}").status_code == 200


def test_admin_can_still_manage_products(client, seeded):
    admin_token = login(client, "admin", "admin123")

    resp = client.post("/api/admin/products", json=NEW_PRODUCT, headers=auth_headers(admin_token))
    assert resp.status_code == 200
    new_id = resp.json()["id"]

    resp = client.put(
        f"/api/admin/products/{new_id}",
        json={**NEW_PRODUCT, "price": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200

    resp = client.delete(f"/api/admin/products/{new_id}", headers=auth_headers(admin_token))
    assert resp.status_code == 200
