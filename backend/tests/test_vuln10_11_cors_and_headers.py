"""Regression tests for VULN-10 (CORS allow-all) and VULN-11 (missing
security headers).

Replays the exploits from docs/VULNERABILITIES.md: sending an arbitrary
Origin and checking for the previously-missing response headers.
"""


def test_cors_does_not_allow_arbitrary_origins(client, seeded):
    resp = client.get("/api/products", headers={"Origin": "https://evil.example.com"})

    assert resp.headers.get("access-control-allow-origin") != "*"
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example.com"


def test_cors_allows_the_real_frontend_origin(client, seeded):
    resp = client.get("/api/products", headers={"Origin": "http://127.0.0.1:5173"})

    assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_security_headers_are_present(client, seeded):
    resp = client.get("/api/products")

    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("content-security-policy") is not None
    assert resp.headers.get("referrer-policy") is not None
