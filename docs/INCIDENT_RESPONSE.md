# Incident Response Plan — SecureCart

A one-page plan covering detection, containment, eradication, recovery and lessons
learned, in terms of SecureCart's actual components. Not a general-purpose IR template -
every step below names the real table, file or command it refers to.

## Detection

SecureCart's `audit_log` table (`backend/database.py`, written by `backend/audit.py`)
records four event types, each with a username (when known), a detail string and a
timestamp:

| `event_type` | Written from | Example `detail` |
|--------------|--------------|---------------------|
| `login_failed` | `login()` (`backend/app.py`) | "invalid username or password" |
| `login_lockout` | `login()` | "login attempted while locked out" |
| `admin_action` | `admin_add_product`/`admin_edit_product`/`admin_delete_product` | "deleted product #7" |
| `authz_denied` | `require_admin()` (`backend/auth.py`) and `order_detail()` (IDOR ownership check) | "non-admin called an admin-only endpoint" / "tried to read order #3 owned by another user" |

Unhandled application errors are logged separately via Python's `logging` module
(`backend/app.py`'s `unhandled_error` handler, `logger.error(...)` with the full
exception and traceback) - the VULN-09 fix. In this coursework setup that goes to
stdout/the console the backend was started from; in a real deployment it would go to a
log aggregator.

**To detect an incident, query `audit_log` for patterns, for example:**

```sql
-- Repeated login_failed for one username in a short window = possible brute force
SELECT username, COUNT(*) FROM audit_log
WHERE event_type = 'login_failed' AND created_at > datetime('now', '-1 hour')
GROUP BY username HAVING COUNT(*) > 10;

-- Any authz_denied at all is worth a look - a legitimate user shouldn't normally
-- hit an admin-only route or someone else's order.
SELECT * FROM audit_log WHERE event_type = 'authz_denied' ORDER BY id DESC;
```

**Example incident:** `audit_log` shows 40 `login_failed` rows for user `alice` in two
minutes, followed by a `login_lockout` row, then (after the lockout window) a
`login_failed` row with a *different* IP pattern than alice's usual one (IP isn't
currently logged - see Lessons Learned) immediately followed by a successful login and
several `authz_denied` rows for admin endpoints. That sequence - brute force, lockout,
eventual success, followed by privilege-escalation attempts - is exactly what the audit
log exists to surface.

## Containment

1. **Revoke the session.** Tokens are short-lived (30 minutes, VULN-06's fix) and
   signed with `SECURECART_JWT_SECRET` (VULN-05's fix). To invalidate *every* existing
   token immediately, rotate the secret: generate a new one
   (`python3 -c "import secrets; print(secrets.token_hex(32))"`), update
   `backend/.env`, and restart the backend. Every previously issued token fails
   signature verification (`decode_token` in `backend/auth.py`) from that point on.
2. **Lock the specific account further if needed.** The built-in lockout
   (`MAX_LOGIN_ATTEMPTS`/`LOGIN_LOCKOUT_SECONDS` in `backend/app.py`) already blocks
   repeated login attempts for 5 minutes after 5 failures; for a confirmed compromise,
   an operator can also directly flip the affected row's `role` to a disabled value or
   change its `password` hash in `backend/securecart.db` to force a re-registration/reset
   flow (there is no self-service password reset in this coursework app - see Lessons
   Learned).
3. **Stop the bleeding on admin endpoints.** If `authz_denied` rows show a specific
   account repeatedly probing `/api/admin/*`, that account's session is already cut by
   step 1; if it's probing via a *valid* admin account that's actually compromised,
   rotating the secret (step 1) and resetting that admin's password (step 2) together
   contain it.

## Eradication

1. Identify how the attacker got in by reading the sequence of `audit_log` rows for the
   affected username/time window (see Detection above) - credential stuffing
   (`login_failed` spam), a forced-browsing/IDOR attempt (`authz_denied` with an order
   ID detail), or a privilege-escalation attempt against an admin route
   (`authz_denied` from `require_admin`).
2. Confirm the relevant fix from `docs/VULNERABILITIES.md` is actually deployed - e.g.
   if the incident looks like VULN-02 (IDOR), confirm the running code has the ownership
   check in `order_detail()` and isn't an old/rolled-back v1 build.
3. If a new flaw (not one of the 12 already tracked) is found, add it to
   `docs/VULNERABILITIES.md` as a new `VULN-xx` entry with the same fields (CWE, OWASP
   category, exploit steps, fix), write a regression test in `backend/tests/` the same
   way the existing fixes were verified, and fix it following the same pattern.

## Recovery

1. Restart the backend with the rotated secret (`backend/.env`) so all new tokens use
   it; confirm with `backend/tests/` (`python -m pytest`) that the full regression
   suite - including every VULN-xx fix - still passes before considering the incident
   closed.
2. Re-run the scan suite (`docs/scans/`, the same Semgrep/Bandit/Gitleaks/pip-audit/npm
   audit/ZAP commands documented in `docs/SCAN_SUMMARY_V1.md` and
   `docs/BEFORE_AFTER.md`) to confirm nothing regressed.
3. If any product data, orders or reviews were tampered with, compare against expected
   seed data (`backend/seed.py`) or a known-good backup of `backend/securecart.db` and
   restore/correct as needed.
4. Notify affected users (in a real deployment) and change any credentials that may
   have been exposed - in this coursework app, that means re-running `backend/seed.py`
   (which generates fresh seed accounts) if the demo database itself was compromised.

## Lessons Learned

After every incident (real or drilled), update:

- **`docs/VULNERABILITIES.md`** - if a new flaw was the root cause, it gets a new entry,
  a fix and a regression test, exactly like VULN-01 through VULN-12.
- **`docs/THREAT_MODEL.md`** - if the incident revealed a threat not already in the
  STRIDE table, add a row.
- **This document** - if detection, containment or recovery took longer than it should
  have because something wasn't logged or wasn't actionable, fix that gap. Two concrete
  gaps already known from building this plan:
  1. **The audit log doesn't record client IP or user agent.** Correlating
     `login_failed`/`authz_denied` rows across a single attacker currently relies on
     username alone. A production version should add an `ip_address` column to
     `audit_log` (`backend/database.py`) and populate it from the request in
     `backend/app.py`.
  2. **There's no token revocation list.** Rotating `SECURECART_JWT_SECRET` invalidates
     *every* session, not just the compromised one, because there's no server-side
     record of individual issued tokens. A production version would track issued token
     IDs (`jti` claims) in a table and support revoking one at a time.
