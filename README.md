# SecureCart

A small e-commerce web app, built twice for the 24CY54 Secure SDLC course project at MSRIT:
a deliberately vulnerable baseline (v1), and a hardened version (v2, this branch) produced
by running SAST/DAST/SCA scans against v1 and fixing every finding.

| Version | Where | Status |
|---------|-------|--------|
| **v1 — vulnerable baseline** | tag `v1.0-vulnerable`, branch `v1-vulnerable` | 12 flaws planted on purpose (see [`docs/VULNERABILITIES.md`](docs/VULNERABILITIES.md)) |
| **v2 — hardened (this branch)** | branch `v2-hardened`, tag `v2.0-hardened` | All 12 flaws fixed, each with a regression test and a CI gate |

> **This is a coursework project, run locally.** It still has no TLS, no production
> deployment hardening, and only the specific controls documented below (e.g. login
> rate-limiting, not general API rate-limiting). Don't expose it to the public internet
> or put real personal data, real passwords, or real card numbers into it.
> The backend binds to `127.0.0.1` only — don't change that.

## What changed between v1 and v2

Every one of the 12 flaws planted in v1 was fixed in v2. The short version:
parameterized SQL queries, an ownership check on order lookups, salted Argon2 password
hashing, login rate-limiting with lockout, an environment-variable JWT secret with
short-lived tokens, sanitized review input (no more raw-HTML rendering), role-based
access control on admin routes, generic error responses (with full detail logged
server-side), CORS locked to the real frontend origin, standard security headers, and
upgraded dependencies with no known CVEs. Each fix also added a pytest regression test
that replays the original exploit and asserts it no longer works.

For the full picture, see:

| Document | What's in it |
|----------|---------------|
| [`docs/VULNERABILITIES.md`](docs/VULNERABILITIES.md) | The flaw register: CWE/OWASP mapping, exploit steps, and each fix's status |
| [`docs/SECURITY_REQUIREMENTS.md`](docs/SECURITY_REQUIREMENTS.md) | Security requirements and abuse/misuse cases behind each fix |
| [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) | Data-flow diagram, trust boundaries, and a STRIDE table |
| [`docs/SCAN_SUMMARY_V1.md`](docs/SCAN_SUMMARY_V1.md) | Baseline scan results against v1 (what each tool did/didn't catch) |
| [`docs/BEFORE_AFTER.md`](docs/BEFORE_AFTER.md) | The same scans re-run against v2, compared side by side |
| [`docs/INCIDENT_RESPONSE.md`](docs/INCIDENT_RESPONSE.md) | Detection/containment/eradication/recovery plan, using the audit log |
| [`docs/SDLC_MAPPING.md`](docs/SDLC_MAPPING.md) | Which artifact in this repo covers each of the six SDLC phases |

## Stack

- **Backend:** FastAPI (Python), raw `sqlite3` (no ORM)
- **Frontend:** React + Vite
- **Database:** SQLite (file created at `backend/securecart.db`)

## Layout

```
backend/    FastAPI app, DB layer, auth/audit modules, seed script, tests/
frontend/   React + Vite single-page app
docs/       Security documentation (see table above) + docs/scans/ (raw tool output)
scripts/    seed.sh and start.sh helpers
.github/    CI security pipeline (.github/workflows/security.yml)
```

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm

## Quick start

```bash
# 1. Install dependencies, generate backend/.env (random JWT secret), and
#    (re)create the database with seed data
./scripts/seed.sh

# 2. Start backend (127.0.0.1:8000) and frontend (127.0.0.1:5173)
./scripts/start.sh
```

Then open <http://127.0.0.1:5173>.

API docs (Swagger UI): <http://127.0.0.1:8000/docs>

`./scripts/seed.sh` can be re-run at any time to reset the database to its initial state.
It also generates `backend/.env` (git-ignored, containing a random `SECURECART_JWT_SECRET`)
on first run if one doesn't already exist — see [`backend/.env.example`](backend/.env.example).

## Running the tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -v
```

One regression test (or more) per fixed vulnerability, under `backend/tests/`, each
named after the `VULN-xx` ID it covers.

## Seed accounts

| Username | Password    | Role  |
|----------|-------------|-------|
| `admin`  | `admin123`  | admin |
| `alice`  | `alice123`  | user  |
| `bob`    | `bob123`    | user  |

These passwords are intentionally simple *demo* credentials (they're hashed with
salted Argon2 — see VULN-03's fix — but simple on purpose, for a course demo). The seed
data also includes ~10 products, a few reviews, and several orders owned by different
users.

## Mock payment

Checkout is a mock. No real payment is processed. Enter any dummy card number
(for example `4242424242424242`); only the last 4 digits are kept on the order.
**Never enter a real card number.**

## Security audit logging

Failed logins, lockouts, admin actions (product add/edit/delete), and authorization
failures (a non-admin hitting an admin route, or a user trying to read someone else's
order) are recorded in the `audit_log` table (`backend/database.py`, written via
`backend/audit.py`). See [`docs/INCIDENT_RESPONSE.md`](docs/INCIDENT_RESPONSE.md) for
how this is meant to be used during an investigation.

## CI: security pipeline (`.github/workflows/security.yml`)

Runs on every push and pull request (also triggerable manually). Six independent jobs,
each failing the build on its own criterion:

| Job | Tool | What it checks | Fails the build on |
|-----|------|-----------------|---------------------|
| `pytest` | pytest | Backend test suite, including one regression test per fixed vulnerability (`backend/tests/`) | Any failing test |
| `semgrep` | Semgrep | Static analysis of `backend/` and `frontend/src/` for security anti-patterns (injection, hardcoded secrets, weak crypto, ...) | Any `ERROR`-severity (high-severity) finding |
| `bandit` | Bandit | Python-specific static analysis of `backend/` app code (SQL building, weak hashes, hardcoded secrets, ...) | Any `HIGH`-severity finding (`-lll`) |
| `gitleaks` | Gitleaks | Scans the full git history for committed secrets/credentials | Any detected secret |
| `pip-audit` | pip-audit | Checks `backend/requirements.txt` against known-CVE databases | Any known vulnerability |
| `npm-audit` | `npm audit` | Checks `frontend/package-lock.json` against npm's advisory database | Any `high`/`critical` severity finding |

See [`docs/SCAN_SUMMARY_V1.md`](docs/SCAN_SUMMARY_V1.md) and
[`docs/BEFORE_AFTER.md`](docs/BEFORE_AFTER.md) for the baseline (v1) and post-fix (v2)
results of these same tools run manually against this repo.
