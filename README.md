> # ⚠️ WARNING: INTENTIONALLY VULNERABLE APPLICATION ⚠️
>
> **SecureCart v1 is deliberately insecure.** It contains planted security flaws
> (SQL injection, IDOR, stored XSS, weak password hashing, missing authorization, and more)
> for the 24CY54 Secure SDLC course project at MSRIT.
>
> - **Run it ONLY on your own machine, on `localhost` / `127.0.0.1`.**
> - **Never deploy it, expose it to a network, put it behind a tunnel, or host it publicly.**
> - **Never reuse real passwords, real card numbers, or real personal data in it.**
> - The backend binds to `127.0.0.1` only. Do not change that.

# SecureCart

A small e-commerce web app built twice for the Secure SDLC course:

| Version | Purpose |
|---------|---------|
| **v1 (this one, tag `v1.0-vulnerable`)** | Deliberately vulnerable baseline. SAST/DAST scans are run against it. |
| v2 (later) | Hardened version after the scan findings are fixed. |

The full list of planted flaws, with exploit steps and intended v2 fixes, is in
[`docs/VULNERABILITIES.md`](docs/VULNERABILITIES.md).

## Stack

- **Backend:** FastAPI (Python), raw `sqlite3` (no ORM)
- **Frontend:** React + Vite
- **Database:** SQLite (file created at `backend/securecart.db`)

## Layout

```
backend/    FastAPI app, DB layer, seed script, requirements.txt
frontend/   React + Vite single-page app
docs/       VULNERABILITIES.md (the flaw register)
scripts/    seed.sh and start.sh helpers
```

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm

## Quick start

```bash
# 1. Install dependencies and (re)create the database with seed data
./scripts/seed.sh

# 2. Start backend (127.0.0.1:8000) and frontend (127.0.0.1:5173)
./scripts/start.sh
```

Then open <http://127.0.0.1:5173>.

API docs (Swagger UI): <http://127.0.0.1:8000/docs>

`./scripts/seed.sh` can be re-run at any time to reset the database to its initial state.

## Seed accounts

| Username | Password    | Role  |
|----------|-------------|-------|
| `admin`  | `admin123`  | admin |
| `alice`  | `alice123`  | user  |
| `bob`    | `bob123`    | user  |

Passwords are intentionally weak. The seed data also includes ~10 products, a few reviews,
and several orders owned by different users so the IDOR is easy to demonstrate.

## Mock payment

Checkout is a mock. No real payment is processed. Enter any dummy card number
(for example `4242424242424242`); only the last 4 digits are kept on the order.
**Never enter a real card number.**
