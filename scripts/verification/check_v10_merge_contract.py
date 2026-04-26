#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    ROOT / "backend" / "smart_agri" / "core" / "tests" / "test_daily_log_governance_api.py",
    ROOT / "backend" / "smart_agri" / "core" / "tests" / "test_activity_cost_snapshot_integrity.py",
    ROOT / "frontend" / "src" / "components" / "daily-log" / "__tests__" / "ActivityItemsField.test.jsx",
    ROOT / "frontend" / "src" / "pages" / "__tests__" / "DailyLogHistory.test.jsx",
    ROOT / "docs" / "reports" / "READINESS_REPORT_INDEX.md",
    ROOT / "docs" / "doctrine" / "DOCX_CODE_TRACEABILITY_MATRIX_V10.md",
    ROOT / "docs" / "doctrine" / "V10_FINAL_CLOSURE_MATRIX.md",
    ROOT / "docs" / "doctrine" / "ENTERPRISE_PRODUCTION_FULL_V10.md",
    ROOT / "docs" / "doctrine" / "RUNTIME_EVIDENCE_GATES_V10.md",
    ROOT / "docs" / "doctrine" / "REMEDIATION_REGISTER_V10.md",
]

missing = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.exists()]
if missing:
    print("FAIL: V10 merge contract is incomplete")
    for item in missing:
        print(item)
    raise SystemExit(1)

matrix = (ROOT / "docs" / "doctrine" / "DOCX_CODE_TRACEABILITY_MATRIX_V10.md").read_text(encoding="utf-8")
expected_mentions = [
    "test_daily_log_governance_api.py",
    "test_activity_cost_snapshot_integrity.py",
    "ActivityItemsField.test.jsx",
    "DailyLogHistory.test.jsx",
]
absent = [name for name in expected_mentions if name not in matrix]
if absent:
    print("FAIL: V10 traceability matrix does not mention all merged test assets")
    for item in absent:
        print(item)
    raise SystemExit(1)

print("PASS: V10 merge contract is complete")
