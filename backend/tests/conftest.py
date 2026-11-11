"""Pytest fixtures: an isolated temp SQLite DB and a FastAPI TestClient per test."""
import os
import sys
from pathlib import Path

# Make `backend/` importable (so `import app`, `import auth`, `import database` work)
# regardless of where pytest is invoked from.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# VULN-05 fix requires this to be set before `auth` is imported; harmless for a
# test-only secret and never used outside this test run.
os.environ.setdefault("SECURECART_JWT_SECRET", "test-secret-for-ci-only-do-not-use")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import database  # noqa: E402
import app as app_module  # noqa: E402
from tests.helpers import seed_standard_data  # noqa: E402


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    monkeypatch.setattr(database, "DB_PATH", path)
    database.init_db()
    return path


@pytest.fixture
def client(db_path):
    return TestClient(app_module.app)


@pytest.fixture
def seeded(client):
    """Admin/alice/bob users, two products, one order each for alice and bob."""
    return seed_standard_data()
