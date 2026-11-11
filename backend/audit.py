"""Security audit logging: failed logins, lockouts, admin actions and
authorization failures. Written to the `audit_log` table (see database.py)
so they can be queried/reported on - see docs/INCIDENT_RESPONSE.md.

Callers pass an open connection and are responsible for committing (the
callers in app.py already commit the surrounding transaction).
"""
from datetime import datetime


def log_event(conn, event_type: str, username: str | None, detail: str) -> None:
    conn.execute(
        "INSERT INTO audit_log (event_type, username, detail, created_at) VALUES (?, ?, ?, ?)",
        (event_type, username, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
