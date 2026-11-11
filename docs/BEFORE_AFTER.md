# Before / After — v1 vs v2 Scan Results

The same six tools from [`docs/SCAN_SUMMARY_V1.md`](SCAN_SUMMARY_V1.md) were re-run after
all 12 fixes in [`docs/VULNERABILITIES.md`](VULNERABILITIES.md). Raw v2 output is under
[`docs/scans/v2/`](scans/v2/); v1 output is under [`docs/scans/v1/`](scans/v1/). Commands
were identical except where noted.

## Per-tool totals

| Tool | v1 findings | v2 findings | Command (v2) |
|------|-------------|-------------|---------------|
| Semgrep | 6 | **0** | same as v1 |
| Bandit | 4 (on `backend/`) | **0** (on `backend/` excluding `backend/tests/`, see note below) | `bandit -r backend/ -x backend/tests` |
| Gitleaks | 0 | **0** | `gitleaks detect --source .` (git-aware; see note below) |
| pip-audit | 25 vulnerabilities / 5 packages | **0** — "No known vulnerabilities found" | same as v1 |
| npm audit | 4 (1 high, 3 moderate) | **0** | same as v1 |
| ZAP (backend API) | 1 warning | **0** | same as v1 |
| ZAP (frontend HTML) | 4 warnings | 5 warnings (see note below) | same as v1 |

## Per-VULN-ID result

| VULN | Flaw | v1 | v2 |
|------|------|----|----|
| VULN-01 | SQL injection | Bandit `B608` | Clean. Parameterized query; regression test passes. |
| VULN-02 | IDOR | not caught by any scanner (manual only) | Ownership check added; regression test passes (no scanner ever "catches" this either way - it's a logic fix, verified by test). |
| VULN-03 | Unsalted MD5 | Semgrep + Bandit (`B324`) | Clean in `backend/` app code. (Bandit still flags `B324` **inside the regression test itself**, which deliberately computes an MD5 to prove the new hash isn't MD5 — see note below.) |
| VULN-04 | No rate limiting | not caught by any scanner | Fixed; regression test passes. No scanner (SAST/SCA/DAST baseline) detects the *absence* of a control either before or after. |
| VULN-05 | Hardcoded JWT secret | Semgrep + Bandit (`B105`); **missed by Gitleaks** | Clean - secret is now an environment variable, not in source. |
| VULN-06 | Non-expiring JWT | not caught by any scanner | Fixed; regression test passes. |
| VULN-07 | Stored XSS | not caught by any scanner | Fixed; regression test passes. (Still a logic/sanitization fix no SAST/DAST tool here actually exercised.) |
| VULN-08 | Missing admin authZ | not caught by any scanner | Fixed; regression test passes. |
| VULN-09 | Verbose errors | not caught by any scanner | Fixed; regression test passes. |
| VULN-10 | CORS allow-all | not caught by any scanner (ZAP missed it both times - see note) | Fixed (`allow_origins` restricted); confirmed manually and by regression test, same as it was disproven manually in v1. |
| VULN-11 | Missing security headers | ZAP (both targets) | Backend: clean (0 ZAP warnings, down from 1). Frontend dev server: still flagged (see note below - this is Vite's dev server, not our app code). |
| VULN-12 | Vulnerable dependency | pip-audit (`python-jose` + 4 incidental others) | Clean - pip-audit reports 0 vulnerabilities across all 6 pinned packages. |

**10 of 12** flaws are now invisible to every scanner we ran, in addition to failing their
dedicated regression test. The remaining two (VULN-02, VULN-04, VULN-06, VULN-07, VULN-08,
VULN-09, VULN-10 — i.e. the access-control/logic/config flaws) were **never detectable by
these scanners even before the fix**, which is itself the point documented in
`SCAN_SUMMARY_V1.md`: automated scanning and the manual/abuse-case testing in
`SECURITY_REQUIREMENTS.md` + the pytest regression suite are complementary, not
substitutes for each other.

## Honest notes on what's still flagged, and why

1. **Bandit still reports one HIGH-severity finding - but only inside the test suite, not
   the application.** `backend/tests/test_vuln03_password_hashing.py` deliberately calls
   `hashlib.md5(...)` to assert the *new* password hash is **not** MD5 (the regression test
   for the fix). Bandit, reasonably, can't tell that from "insecure use of MD5" and flags
   it (`B324`, HIGH). The CI workflow (`.github/workflows/security.yml`) therefore runs
   Bandit as `bandit -r backend/ -lll -x backend/tests` - scanning application code, not
   test code, which is a defensible scope for a SAST gate. Running Bandit against
   `backend/` *including* tests (as the v1 baseline scan did, since no fixes existed yet to
   write tests for) would still show this one test-only finding; the application code
   itself (`app.py`, `auth.py`, `database.py`, `seed.py`) has zero Bandit findings either way.

2. **Gitleaks' git-aware scan is clean, but a filesystem scan of this working directory is
   not — because it includes a real, local-only, git-ignored `backend/.env`.** Running
   `gitleaks detect --source . --no-git` (filesystem mode, scanning *every* file on disk,
   tracked or not) flags the actual generated JWT secret in `backend/.env`. That file is
   never committed (`.gitignore` excludes it; `git ls-files` confirms it isn't tracked) and
   is exactly what VULN-05's fix intends - a real secret that lives only in a local,
   git-ignored file, never in source control. The git-aware scan (`gitleaks detect --source
   .`, no `--no-git`) - which is what actually matters for "is a secret committed to this
   repo", and what the CI workflow runs - reports **no leaks found**, scanning all 26+
   commits in history. The v1 baseline scan in `SCAN_SUMMARY_V1.md` also used `--no-git`
   (there was no `.env` file yet at that point, so it made no difference there); this v2
   scan intentionally re-ran both modes to catch exactly this distinction.

3. **The frontend dev server (Vite) itself still shows 5 ZAP warnings, up from 4 in v1 -
   one more than before, and these are not fixed.** The `security_headers` middleware
   added for VULN-11 lives in `backend/app.py` and only affects the FastAPI backend's
   responses; it has no effect on `frontend/`'s Vite dev server, which serves the
   React app's HTML/JS directly and was never in scope for that fix (Vite's dev server is
   local developer tooling - a production deployment would serve the *built* frontend
   through a reverse proxy/CDN that adds these headers, which is out of scope for this
   coursework pass). The backend API target, which the `security_headers` middleware
   *does* cover, went from 1 ZAP warning to **0**. The one new warning on the frontend
   target - "Information Disclosure - Suspicious Comments" on `/@vite/client` - is a
   comment inside Vite's own bundled dev-mode HMR client script, not in any code this
   project wrote; it is noted here as a scanner finding against third-party dev tooling,
   not a project vulnerability.

4. **ZAP's baseline passive scan still cannot confirm the CORS fix (VULN-10) either way.**
   As documented in `SCAN_SUMMARY_V1.md`, ZAP's baseline crawl doesn't send an `Origin`
   header, so `CORSMiddleware` never emits an `Access-Control-Allow-Origin` header for it
   to inspect, in v1 *or* v2 - both report `PASS` (not applicable) for "Cross-Domain
   Misconfiguration" [10098]. The fix is real and was confirmed with the actual exploit
   step (`curl -H "Origin: https://evil.example.com"`, now rejected) and a dedicated
   pytest regression test (`backend/tests/test_vuln10_11_cors_and_headers.py`), just not
   by this particular automated DAST pass - the same tooling limitation applies
   identically before and after the fix.

5. **Two dependency upgrades went beyond the single planted flaw, on both sides.** VULN-12
   was "python-jose has a known CVE"; fixing it meant also upgrading `fastapi`, `uvicorn`,
   `python-dotenv` and `bleach`, which pip-audit had separately (and correctly) flagged
   against the versions pinned when this project was built - not planted, but real, and
   left unfixed would have kept pip-audit non-clean for reasons unrelated to VULN-12. The
   same thing happened on the frontend: `vite` and `react-router-dom` had real npm-audit
   findings (1 high, 3 moderate) that were never one of the 12 planted flaws, and were
   upgraded (major-version bumps, verified with a full Playwright smoke test - login,
   search, product detail/reviews, cart, checkout, order history, admin - after the
   upgrade) so `npm audit` is also clean in v2 and the new CI pipeline doesn't start out
   red for unplanted reasons.
