"""Regression test for VULN-09 (verbose errors leaking stack traces/SQL).

Forces an unhandled exception and checks the client gets a generic message
(no exception text, no traceback, no SQL) while the detail is still logged
server-side for operators to investigate.
"""
import logging

from fastapi.testclient import TestClient

import app as app_module


def test_unhandled_exception_returns_generic_message_not_details(db_path, monkeypatch, caplog):
    def boom():
        raise RuntimeError("sensitive internal detail: SELECT * FROM users WHERE 1=1")

    monkeypatch.setattr(app_module, "get_db", boom)
    # TestClient re-raises unhandled exceptions by default; disable that so we
    # can inspect the HTTP response our own exception handler produces.
    local_client = TestClient(app_module.app, raise_server_exceptions=False)

    with caplog.at_level(logging.ERROR, logger="securecart"):
        resp = local_client.get("/api/products")

    assert resp.status_code == 500
    body = resp.json()
    assert body["error"] == "Internal server error. Please try again later."
    assert "error_id" in body

    assert "sensitive internal detail" not in resp.text
    assert "SELECT" not in resp.text
    assert "Traceback" not in resp.text
    assert "RuntimeError" not in resp.text

    # ... but it WAS captured server-side, for operators to investigate.
    assert any("sensitive internal detail" in rec.message for rec in caplog.records)
