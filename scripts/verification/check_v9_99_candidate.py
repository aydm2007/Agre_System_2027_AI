#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
files = [
    ROOT / "docs/doctrine/V9_FINAL_CLOSURE_MATRIX.md",
    ROOT / "docs/doctrine/ENTERPRISE_PRODUCTION_FULL_V9.md",
    ROOT / "docs/doctrine/RUNTIME_EVIDENCE_GATES_V9.md",
    ROOT / "docs/reports/REMEDIATION_REGISTER_V9.md",
    ROOT / "docs/doctrine/DOCX_CODE_TRACEABILITY_MATRIX_V9.md",
]
for p in files:
    if not p.exists():
        print(f'FAIL: missing {p.relative_to(ROOT)}')
        sys.exit(1)
print('PASS: V9 99-candidate doctrine pack is present')
