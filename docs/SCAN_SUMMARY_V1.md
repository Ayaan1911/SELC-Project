# Baseline Scan Summary — v1 (intentionally vulnerable)

Scans run against the `v2-hardened` branch **before any fixes were applied** (i.e. the
v1 code, same as `v1-vulnerable`). The backend was running on `http://127.0.0.1:8000`
and the frontend dev server on `http://127.0.0.1:5173`, both loopback-only. Raw tool
output is under [`docs/scans/v1/`](scans/v1/).

| Tool | Command | Raw output |
|------|---------|------------|
| Semgrep 1.185.0 | `semgrep --config p/security-audit --config p/owasp-top-ten --config p/python --config p/javascript --config p/secrets --json backend/ frontend/src/` | `scans/v1/semgrep.json` |
| Bandit 1.9.4 | `bandit -r backend/ -f json` | `scans/v1/bandit.json` |
| Gitleaks 8.21.2 | `gitleaks detect --source . --no-git` | `scans/v1/gitleaks.json` |
| pip-audit 2.10.1 | `pip-audit -r backend/requirements.txt -f json` | `scans/v1/pip-audit.json` |
| npm audit | `npm audit --json` (in `frontend/`) | `scans/v1/npm-audit.json` |
| OWASP ZAP (`zaproxy/zap-stable`, baseline) | `zap-baseline.py -t http://127.0.0.1:8000/api/products` | `scans/v1/zap-report.json`, `zap-report.html`, `zap-console.txt` |
| OWASP ZAP (baseline, frontend) | `zap-baseline.py -t http://127.0.0.1:5173/` | `scans/v1/zap-frontend-report.json`, `zap-frontend-report.html`, `zap-frontend-console.txt` |

ZAP ran via Docker (`zaproxy/zap-stable` pulled from Docker Hub — the `ghcr.io/zaproxy/zaproxy`
image's blob CDN was not reachable from this session's network, so Docker Hub was used
instead; functionally identical image). Both backend and frontend were scanned because
ZAP's passive header/clickjacking rules mostly fire on HTML responses, not JSON APIs — see
the ZAP row below.

## Findings per tool, mapped to VULN IDs

### Semgrep — 6 findings

| Finding | File:line | VULN ID |
|---------|-----------|---------|
| `python.fastapi.security.wildcard-cors` | `backend/app.py:26` | VULN-10 |
| `python.lang.security.insecure-hash-algorithms-md5` (×2) | `backend/auth.py:17`, `:21` | VULN-03 |
| `python.lang.security.audit.md5-used-as-password` (×2) | `backend/auth.py:17`, `:21` | VULN-03 |
| `python.jwt.security.jwt-hardcode.jwt-python-hardcoded-secret` | `backend/auth.py:32` | VULN-05 |

**Did not catch:** VULN-01 (SQLi — the specific string-concatenation pattern used here
wasn't matched by any rule in these packs), VULN-02 (IDOR — business-logic flaw, not a
syntactic pattern), VULN-04 (absence of rate limiting), VULN-06 (missing `exp` claim —
absence of a field, not a pattern), VULN-07 (`dangerouslySetInnerHTML` was *not* flagged
by the `p/javascript`/`p/owasp-top-ten` packs used here), VULN-08 (missing admin role
check — logic flaw), VULN-09 (verbose errors), VULN-11 (missing headers), VULN-12
(dependency CVEs — SAST tools don't do SCA).

### Bandit — 4 findings

| Finding | File:line | VULN ID |
|---------|-----------|---------|
| `B608 hardcoded_sql_expressions` | `backend/app.py:132` | VULN-01 |
| `B105 hardcoded_password_string` | `backend/auth.py:10` | VULN-05 (Bandit's heuristic flags any literal assigned to a secret-like name) |
| `B324 hashlib` (×2) | `backend/auth.py:17`, `:21` | VULN-03 |

**Did not catch:** VULN-02, VULN-04, VULN-06, VULN-07 (Bandit only scans Python, so the
frontend JSX sink is out of scope — the backend side of VULN-07, storing text
unsanitized, also isn't a Bandit rule), VULN-08, VULN-09, VULN-10, VULN-11, VULN-12
(no SCA).

### Gitleaks — 0 findings

**Did not catch VULN-05** (hardcoded JWT secret `"securecart-secret-key-123"`), even
though it is exactly the kind of thing a secrets scanner is meant to find. Gitleaks'
default rule set matches known vendor token *formats* (AWS keys, Slack tokens, private
key blocks, high-entropy strings, etc.); a short, dictionary-like, English string
assigned to `SECRET_KEY` has neither a recognizable prefix nor enough Shannon entropy to
trip the generic rules. This is a real, useful gap to call out: a custom high-signal
rule (e.g. matching `SECRET_KEY\s*=\s*["\'][^"\']+["\']` in this codebase) would be
needed to catch this specific pattern — Bandit's heuristic (above) caught it instead.

### pip-audit — 25 known vulnerabilities across 5 packages

| Package | Version | VULN ID | Notes |
|---------|---------|---------|-------|
| `python-jose` | 3.3.0 | **VULN-12** | CVE-2024-33663, CVE-2024-33664 (+2 more PYSEC IDs) — the planted flaw. |
| `fastapi` | 0.104.1 | not planted | PYSEC-2024-38 (ReDoS in `python-multipart` via FastAPI's form parsing). |
| `starlette` | 0.27.0 | not planted | 7 distinct advisories (DoS / multipart parsing issues), fixed in later 0.4x/1.x releases. |
| `anyio` | 3.7.1 | not planted | 2 advisories, fixed in 4.x. |
| `ecdsa` | 0.19.2 | not planted | 1 advisory (timing side-channel), transitive via `python-jose[cryptography]`. |

**Honest note:** pip-audit correctly found the one dependency we deliberately pinned
with a known CVE (VULN-12), but it *also* surfaced CVEs in `fastapi`, `starlette`,
`anyio` and `ecdsa` that were never intentionally planted — they were simply pinned to
versions current at the time this project was built, and newer CVEs have since been
published against them. This is realistic: an SCA tool reports every known-vulnerable
version it sees, planted or not. The v2 fix for VULN-12 takes the opportunity to
upgrade all of these, not just `python-jose`.

### npm audit — 4 findings (0 critical, 1 high, 3 moderate)

| Package | Severity | Notes |
|---------|----------|-------|
| `vite` | high | Dev-server-only path traversal / cross-origin issues in Vite's dev middleware. |
| `react-router` / `react-router-dom` | moderate | Open-redirect / SSR hydration issues (SSR is not used here). |
| `esbuild` | moderate | Dev server can be reached from any website (same class of issue as `vite`'s). |

**Not related to any planted VULN ID.** These are frontend *build tooling* dependency
issues (dev server only), not application code. They don't map to the 12 planted flaws
and are out of scope for this pass, but are reported here for completeness since `npm
audit` was run as requested.

### OWASP ZAP (DAST)

**Against the backend API (`/api/products`, JSON response), 1 of 62 rules warned:**

- `WARN-NEW: X-Content-Type-Options Header Missing [10021]` → part of **VULN-11**.

**Did not catch** `Content-Security-Policy`/`X-Frame-Options`/anti-clickjacking rules
on this target — ZAP's passive rules for those mostly evaluate `text/html` responses,
and `/api/products` returns `application/json`, so they reported **PASS** (not
applicable) rather than flagging the real gap. **Cross-Domain Misconfiguration [10098]**
also **PASSED**: Starlette's `CORSMiddleware` only emits `Access-Control-Allow-Origin`
when the request carries an `Origin` header, and ZAP's baseline crawl doesn't send one
by default — so the wildcard-CORS misconfiguration (VULN-10), which *was* confirmed
manually with `curl -H "Origin: https://evil.example.com"` (see
[`VULNERABILITIES.md`](VULNERABILITIES.md)), was invisible to this automated DAST pass.
ZAP also could not crawl past the single JSON endpoint given, could not authenticate,
and (baseline mode is passive-only) never attempted the SQLi/IDOR/XSS/missing-authZ
payloads that were confirmed manually — those require either ZAP's active scan mode
with authentication configured, or a hand-crafted payload, neither of which baseline
mode does out of the box.

**Against the frontend (`/`, HTML response), 4 warnings:**

- `Missing Anti-clickjacking Header [10020]` → **VULN-11**
- `X-Content-Type-Options Header Missing [10021]` (×5) → **VULN-11**
- `Content Security Policy (CSP) Header Not Set [10038]` (×3) → **VULN-11**
- `Modern Web Application [10109]` (informational: flags the app as an SPA, explaining
  why the spider could not crawl further without JS rendering/ajax-spider)

The frontend target did catch the full set of missing-header issues (because it serves
real HTML), confirming the value of scanning both tiers. It did not and could not catch
VULN-01/02/07/08/09 (server-side logic/injection flaws) or VULN-10 (CORS, same reason as
above — Vite's dev server doesn't reflect the backend's CORS policy at all).

## Summary: what automated scanning caught vs. missed, per VULN ID

| VULN | Planted flaw | Caught by |
|------|--------------|-----------|
| VULN-01 | SQL injection | Bandit (static) |
| VULN-02 | IDOR | **none** (manual testing only — business logic) |
| VULN-03 | Unsalted MD5 | Semgrep, Bandit |
| VULN-04 | No rate limiting | **none** (manual testing only — absence of a control) |
| VULN-05 | Hardcoded JWT secret | Semgrep, Bandit (Gitleaks missed it) |
| VULN-06 | Non-expiring JWT | **none** (manual testing only) |
| VULN-07 | Stored XSS | **none** of the automated tools (manual testing only) |
| VULN-08 | Missing admin authZ | **none** (manual testing only — business logic) |
| VULN-09 | Verbose errors | **none** (manual testing only) |
| VULN-10 | CORS allow-all | **none** of the automated scans (ZAP missed it; confirmed manually) |
| VULN-11 | Missing security headers | ZAP (both targets) |
| VULN-12 | Vulnerable dependency | pip-audit |

**Takeaway:** SAST (Semgrep/Bandit) is good at syntactic/crypto anti-patterns and
hardcoded secrets; SCA (pip-audit/npm audit) is good at known-CVE dependencies; DAST
(ZAP baseline) is good at missing-header/clickjacking checks on HTML pages but, run
unauthenticated and passively against a JSON API, missed every access-control,
injection and business-logic flaw in this app. None of the six tools, run out of the
box, found the IDOR, missing-admin-authZ, stored-XSS, verbose-error, no-rate-limit or
CORS flaws — those were only confirmed by the manual exploit steps in
[`VULNERABILITIES.md`](VULNERABILITIES.md). This is the practical argument for pairing
automated scanning with manual/abuse-case testing (see
[`SECURITY_REQUIREMENTS.md`](SECURITY_REQUIREMENTS.md)) rather than relying on either alone.
