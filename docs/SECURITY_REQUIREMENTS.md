# Security Requirements & Abuse/Misuse Cases

Security requirements for SecureCart, grouped by category. Each requirement has an ID
(`SR-xx`) and lists the v1 planted vulnerability IDs (`VULN-xx`, see
[`VULNERABILITIES.md`](VULNERABILITIES.md)) it addresses. Each category also lists at
least one abuse/misuse case: how an attacker tries to defeat the requirement, and what
the system must do instead.

## Authentication

| ID | Requirement | Related VULN IDs |
|----|-------------|-------------------|
| SR-01 | Passwords must be hashed with a slow, salted algorithm (Argon2) before storage; plaintext or raw password must never be logged or stored. | VULN-03 |
| SR-02 | The login endpoint must rate-limit and temporarily lock an account/IP after repeated failed attempts. | VULN-04 |
| SR-03 | JWTs must be signed with a secret loaded from environment configuration, never committed to source control, and the app must refuse to start without it. | VULN-05 |
| SR-04 | JWTs must carry a short expiry (`exp`) and be rejected once expired. | VULN-06 |

**Abuse/misuse case AM-01 — Credential stuffing / brute force.**
*Misuse:* an attacker scripts thousands of login attempts against known usernames with a
leaked password list. *Required behavior:* after N failed attempts the account is
locked for a cool-down period and further attempts are rejected (SR-02), and even a
successful guess only yields a short-lived, properly signed token (SR-03, SR-04), limiting
the blast radius of any one compromised credential.

**Abuse/misuse case AM-02 — Offline cracking of a stolen database.**
*Misuse:* an attacker who obtains a copy of the `users` table (e.g. via SR-07 failing)
attempts to recover plaintext passwords. *Required behavior:* Argon2 with a per-user
salt makes bulk/rainbow-table cracking computationally infeasible (SR-01).

## Authorization

| ID | Requirement | Related VULN IDs |
|----|-------------|-------------------|
| SR-05 | A user may only read or modify their own cart and orders; admins may read any order for support purposes but regular users may not. | VULN-02 |
| SR-06 | Every `/api/admin/*` endpoint must verify the caller's role is `admin`, not merely that they are logged in. | VULN-08 |

**Abuse/misuse case AM-03 — IDOR / forced browsing.**
*Misuse:* a logged-in regular user increments the `order_id` in `GET /api/orders/{id}`
to read other customers' orders. *Required behavior:* the server checks
`order.user_id == current_user.id` (or `role == admin`) before returning data (SR-05).

**Abuse/misuse case AM-04 — Privilege escalation via direct API calls.**
*Misuse:* a regular user who inspects the frontend finds and calls
`POST /api/admin/products` directly (bypassing the UI, which hides the Admin link).
*Required behavior:* the server itself enforces the admin role on every admin route,
independent of what the UI shows or hides (SR-06).

## Data Protection

| ID | Requirement | Related VULN IDs |
|----|-------------|-------------------|
| SR-07 | Only the minimum payment data needed is retained (last 4 digits); no full card number, CVV or expiry is ever persisted or logged. | (checkout was never vulnerable in this sense; kept as a standing requirement) |
| SR-08 | API responses must not leak internal state (stack traces, SQL text, file paths) to clients; errors are logged server-side with full detail and returned to clients generically. | VULN-09 |
| SR-09 | Cross-origin requests to the API are restricted to the known frontend origin; browsers must not be able to read API responses from arbitrary third-party pages. | VULN-10 |
| SR-10 | Responses must include standard security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, HSTS where applicable) to reduce the impact of any residual injection or framing issue. | VULN-11 |

**Abuse/misuse case AM-05 — Information disclosure via errors.**
*Misuse:* an attacker sends malformed input to trigger a 500 response and reads the
stack trace / raw SQL to learn the schema and craft a more precise injection.
*Required behavior:* the client only ever sees a generic message and a correlation ID;
the detail goes to a server-side log (SR-08).

**Abuse/misuse case AM-06 — Malicious third-party site riding on a logged-in session.**
*Misuse:* a victim who is logged into SecureCart visits `evil.example.com`, which makes
background requests to the SecureCart API hoping the browser/CORS policy allows it to
read the response. *Required behavior:* `Access-Control-Allow-Origin` only ever names
the real frontend origin, so the browser blocks the cross-origin read (SR-09).

## Input Handling

| ID | Requirement | Related VULN IDs |
|----|-------------|-------------------|
| SR-11 | All database queries must use parameterized statements; user input is never concatenated into SQL text. | VULN-01 |
| SR-12 | User-supplied text (e.g. product reviews) must be validated/sanitized on the backend and rendered as plain text (not raw HTML) on the frontend. | VULN-07 |

**Abuse/misuse case AM-07 — SQL injection via search.**
*Misuse:* an attacker appends `' UNION SELECT ... FROM users--` to the product search
box to dump the `users` table through an endpoint that was only meant to filter
products. *Required behavior:* the query is built with bound parameters, so injected
SQL syntax is treated as a literal search string, not executable SQL (SR-11).

**Abuse/misuse case AM-08 — Stored XSS via reviews.**
*Misuse:* an attacker posts a review containing `<img src=x onerror=...>`; every later
visitor to that product page (including an admin) executes the attacker's script in
their own session. *Required behavior:* the backend rejects/strips HTML from review
text and the frontend renders it as text, never as HTML (SR-12).

## Logging & Monitoring

| ID | Requirement | Related VULN IDs |
|----|-------------|-------------------|
| SR-13 | Failed logins, account lockouts, admin actions (product create/edit/delete) and authorization failures must be recorded with a timestamp, actor (where known) and outcome, for later incident investigation. | VULN-04, VULN-08 (detective control for both) |

**Abuse/misuse case AM-09 — Undetected intrusion.**
*Misuse:* an attacker who succeeds despite the above controls operates quietly, and
without logs no one notices until damage is done. *Required behavior:* security-relevant
events are durably logged so an investigation (see
[`docs/INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md)) can reconstruct what happened
(SR-13).

## Dependency Management

| ID | Requirement | Related VULN IDs |
|----|-------------|-------------------|
| SR-14 | Third-party dependencies with known, fixed-in-a-newer-version CVEs must be upgraded (or replaced) and the fix verified with a dependency scanner (`pip-audit`, `npm audit`). | VULN-12 |

**Abuse/misuse case AM-10 — Exploiting a known library CVE.**
*Misuse:* an attacker fingerprints the JWT library version and uses a public CVE
(algorithm confusion) to forge tokens without ever touching application code.
*Required behavior:* dependencies are kept at versions with no known unpatched CVEs,
verified continuously in CI (SR-14, enforced by `.github/workflows/security.yml`).
