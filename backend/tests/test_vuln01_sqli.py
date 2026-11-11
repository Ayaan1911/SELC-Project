"""Regression test for VULN-01 (SQL injection in product search).

Replays the exact exploit from docs/VULNERABILITIES.md and asserts it no
longer works: the UNION payload must be treated as a literal search string,
not executable SQL, and must not leak any row from the `users` table.
"""
import json


def test_union_injection_no_longer_leaks_users(client, seeded):
    payload = "nonexistent' UNION SELECT id, username, password, role, 1 FROM users--"
    resp = client.get("/api/products/search", params={"q": payload})

    assert resp.status_code == 200
    results = resp.json()
    assert results == []  # no product name contains that literal string

    body_text = json.dumps(results)
    assert "alice" not in body_text
    assert "bob" not in body_text
    assert "admin" not in body_text


def test_unbalanced_quote_no_longer_breaks_the_query(client, seeded):
    """The old vulnerable query broke (and leaked the raw SQL error) on a
    bare quote; a parameterized query treats it as an ordinary character."""
    resp = client.get("/api/products/search", params={"q": "Widget'"})

    assert resp.status_code == 200
    assert resp.json() == []  # no product literally named "Widget'"


def test_search_still_works_normally(client, seeded):
    resp = client.get("/api/products/search", params={"q": "Widget"})

    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Widget" in names
    assert "Gadget" not in names
