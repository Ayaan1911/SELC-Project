"""Regression test for VULN-03 (passwords stored as unsalted MD5).

Confirms passwords are no longer stored as unsalted MD5, are now salted
(two hashes of the same password differ), and that login still works.
"""
import hashlib

import auth
from tests.helpers import login


def test_stored_hash_is_not_md5():
    stored = auth.hash_password("admin123")

    assert stored != hashlib.md5(b"admin123").hexdigest()


def test_hash_is_salted_same_password_different_output():
    first = auth.hash_password("admin123")
    second = auth.hash_password("admin123")

    assert first != second  # a fixed, unsalted hash would be identical every time


def test_login_still_works_with_the_new_hash(client, seeded):
    token = login(client, "alice", "alice123")  # raises via helper if login fails
    assert token


def test_login_rejects_wrong_password(client, seeded):
    resp = client.post("/api/login", json={"username": "alice", "password": "wrong"})

    assert resp.status_code == 401
