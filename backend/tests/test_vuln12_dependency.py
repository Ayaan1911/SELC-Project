"""Regression test for VULN-12 (dependency with a known CVE).

Confirms python-jose is no longer a dependency and that pip-audit finds no
known vulnerabilities in backend/requirements.txt.
"""
import json
import subprocess
import sys
from pathlib import Path

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"


def test_python_jose_is_no_longer_a_dependency():
    # Ignore comment lines (the register/comment above intentionally mentions
    # "python-jose" by name as a historical note).
    dependency_lines = [
        line for line in REQUIREMENTS.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert not any("python-jose" in line for line in dependency_lines)
    assert any(line.lower().startswith("pyjwt") for line in dependency_lines)


def test_pip_audit_reports_no_known_vulnerabilities():
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "-r", str(REQUIREMENTS), "-f", "json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"pip-audit found issues:\n{result.stdout}\n{result.stderr}"
    report = json.loads(result.stdout)
    vulnerable = [d for d in report.get("dependencies", []) if d.get("vulns")]
    assert vulnerable == [], f"pip-audit flagged: {vulnerable}"
