"""Regression test for VULN-07 (stored XSS in product reviews).

Replays the exploit from docs/VULNERABILITIES.md: posting a review containing
an HTML/script payload. The backend must no longer store it as executable
HTML (the frontend fix - rendering as text instead of dangerouslySetInnerHTML
- is verified separately, by inspection/code review, since this suite only
exercises the backend).
"""
from tests.helpers import auth_headers, login


def test_html_payload_is_stripped_from_stored_review(client, seeded):
    token = login(client, "alice", "alice123")
    payload = "Nice! <img src=x onerror=\"document.title='XSS-FIRED'\">"

    resp = client.post(
        f"/api/products/{seeded['product1']}/reviews",
        json={"rating": 1, "review_text": payload},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200

    detail = client.get(f"/api/products/{seeded['product1']}").json()
    stored = detail["reviews"][0]["review_text"]

    assert "<img" not in stored
    assert "onerror" not in stored
    assert "<" not in stored and ">" not in stored


def test_plain_text_review_is_preserved(client, seeded):
    token = login(client, "alice", "alice123")

    resp = client.post(
        f"/api/products/{seeded['product1']}/reviews",
        json={"rating": 5, "review_text": "Great product, fast shipping!"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200

    detail = client.get(f"/api/products/{seeded['product1']}").json()
    assert detail["reviews"][0]["review_text"] == "Great product, fast shipping!"


def test_empty_review_after_stripping_tags_is_rejected(client, seeded):
    token = login(client, "alice", "alice123")

    resp = client.post(
        f"/api/products/{seeded['product1']}/reviews",
        json={"rating": 3, "review_text": "<script></script>"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 422


def test_rating_out_of_range_is_rejected(client, seeded):
    token = login(client, "alice", "alice123")

    resp = client.post(
        f"/api/products/{seeded['product1']}/reviews",
        json={"rating": 99, "review_text": "ok"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 422
