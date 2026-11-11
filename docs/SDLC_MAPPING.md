# Secure SDLC Artifact Mapping

SecureCart maps its artifacts onto the six phases of the Secure SDLC used for the
24CY54 course. Rows are updated as the v2 (hardened) pass produces each artifact.

| Phase | Artifact in this repo | Status |
|-------|------------------------|--------|
| **1. Requirements** | `docs/SECURITY_REQUIREMENTS.md` — security requirements and abuse/misuse cases | pending |
| **2. Design** | `docs/THREAT_MODEL.md` — data-flow diagram, trust boundaries, STRIDE table | pending |
| **3. Implementation** | `backend/`, `frontend/` source code; `docs/VULNERABILITIES.md` (v1 planted flaws) and their fixes in v2 | v1 done ([`docs/VULNERABILITIES.md`](VULNERABILITIES.md)); v2 fixes: pending |
| **4. Testing** | `docs/scans/v1/`, `docs/SCAN_SUMMARY_V1.md` (baseline SAST/DAST/SCA), `backend/tests/` (pytest regression tests per VULN ID), `docs/scans/v2/`, `docs/BEFORE_AFTER.md` | pending |
| **5. Deployment** | `.github/workflows/security.yml` — CI security pipeline (pytest, Semgrep, Bandit, Gitleaks, pip-audit, npm audit) gating merges | pending |
| **6. Maintenance** | Security audit logging (`backend/`), `docs/INCIDENT_RESPONSE.md` — detection/containment/eradication/recovery/lessons-learned plan | pending |

## Notes

- v1 (tag `v1.0-vulnerable` / branch `v1-vulnerable`) deliberately skips phases 1, 2, 4
  (beyond ad hoc exploit testing), 5 and 6 — it exists only to give the v2 pass
  something real to scan and fix.
- v2 (branch `v2-hardened`) fills in every phase above; this table is completed in
  the final step of that pass.
