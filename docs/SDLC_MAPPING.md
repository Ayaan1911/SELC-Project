# Secure SDLC Artifact Mapping

SecureCart maps its artifacts onto the six phases of the Secure SDLC used for the
24CY54 course.

| Phase | Artifact in this repo | Status |
|-------|------------------------|--------|
| **1. Requirements** | [`docs/SECURITY_REQUIREMENTS.md`](SECURITY_REQUIREMENTS.md) — 14 security requirements (`SR-01`..`SR-14`) across authentication, authorization, data protection, input handling, logging and dependency management, plus 10 abuse/misuse cases (`AM-01`..`AM-10`), each tied to the `VULN-xx` ID(s) it addresses | **Done** |
| **2. Design** | [`docs/THREAT_MODEL.md`](THREAT_MODEL.md) — Mermaid data-flow diagram with four trust boundaries (browser, frontend origin, API process, database) and a STRIDE table mapping every planted vulnerability to its threat category and planned mitigation | **Done** |
| **3. Implementation** | `backend/`, `frontend/` source code. v1's planted flaws and v2's fixes are both tracked in [`docs/VULNERABILITIES.md`](VULNERABILITIES.md) — one entry per flaw, each now marked "FIXED in v2" with the file/function that fixes it | **Done** (v1 planted on branch `v1-vulnerable`/tag `v1.0-vulnerable`; v2 fixes on branch `v2-hardened`/tag `v2.0-hardened`) |
| **4. Testing** | Baseline scans: [`docs/scans/v1/`](scans/v1/) + [`docs/SCAN_SUMMARY_V1.md`](SCAN_SUMMARY_V1.md). Regression tests: `backend/tests/` (one pytest file per `VULN-xx`, each replaying the original exploit and asserting it now fails, plus `test_audit_logging.py`). Re-scan: [`docs/scans/v2/`](scans/v2/) + [`docs/BEFORE_AFTER.md`](BEFORE_AFTER.md) comparing v1 vs v2 per tool and per VULN ID | **Done** |
| **5. Deployment** | [`.github/workflows/security.yml`](../.github/workflows/security.yml) — CI security pipeline (pytest, Semgrep, Bandit, Gitleaks, pip-audit, npm audit) running on every push/PR, gating merges on each tool's own severity threshold; documented in [`README.md`](../README.md#ci-security-pipeline-githubworkflowssecurityyml) | **Done** |
| **6. Maintenance** | Security audit logging: the `audit_log` table (`backend/database.py`, written by `backend/audit.py`) records failed logins, lockouts, admin actions and authorization failures. [`docs/INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md) — detection/containment/eradication/recovery/lessons-learned plan built around that log, with example queries and two honestly-scoped known gaps (no IP logging, no per-token revocation) | **Done** |

## Notes

- v1 (tag `v1.0-vulnerable`, branch `v1-vulnerable`) deliberately skips phases 1, 2, 4
  (beyond ad hoc manual exploit testing), 5 and 6 — it exists only to give the v2 pass
  something real to scan and fix, per the course assignment.
- v2 (branch `v2-hardened`, tag `v2.0-hardened`) fills in every phase above, in the same
  order as the numbered steps that produced it.
