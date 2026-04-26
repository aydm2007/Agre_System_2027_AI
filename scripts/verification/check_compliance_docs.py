from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


REQUIRED_DOCS: dict[str, list[str]] = {
    "docs/compliance/ISMS_SCOPE_AND_RISK_REGISTER.md": [
        "## Scope",
        "## Risk Register",
        "acceptance_criteria",
    ],
    "docs/compliance/SECURITY_CONTROLS_MATRIX.md": [
        "ISO_27001_family",
        "NIST_CSF",
        "COBIT_process",
        "evidence_path",
        "test_command",
    ],
    "docs/compliance/DR_BCP_RUNBOOK.md": [
        "RTO_target_minutes",
        "RPO_target_minutes",
        "Monthly Drill Requirements",
    ],
    "docs/compliance/DATA_GOVERNANCE_STANDARD.md": [
        "## Data Classification",
        "## Retention Schedule",
        "## PII and Sensitive Data Handling",
    ],
    "docs/compliance/RELEASE_GOVERNANCE_STANDARD.md": [
        "## Environment Segregation",
        "## Merge Blocking Conditions",
        "## Evidence Requirements per Release",
    ],
    "docs/reports/GLOBAL_BASELINE_GAP_REGISTER.md": [
        "gap_id",
        "control_family",
        "owner",
        "due_date",
        "evidence",
    ],
}


def main() -> int:
    missing: list[str] = []
    invalid: list[str] = []

    for rel_path, required_tokens in REQUIRED_DOCS.items():
        abs_path = REPO_ROOT / rel_path
        if not abs_path.exists():
            missing.append(rel_path)
            continue

        content = abs_path.read_text(encoding="utf-8", errors="replace")
        missing_tokens = [token for token in required_tokens if token not in content]
        if missing_tokens:
            invalid.append(f"{rel_path} missing tokens: {missing_tokens}")

    if missing:
        print("BLOCK: Missing required compliance docs:")
        for rel in missing:
            print(f"- {rel}")

    if invalid:
        print("BLOCK: Incomplete required compliance docs:")
        for line in invalid:
            print(f"- {line}")

    if missing or invalid:
        return 1

    print("PASS: All required compliance documentation files and mandatory sections are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
