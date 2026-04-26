#!/usr/bin/env python3
"""Ensure every documentary-cycle file under Docx is mapped in the latest traceability matrix."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCX_DIR = ROOT / "Docx"
MATRIX_CANDIDATES = [
    ROOT / "docs" / "doctrine" / "DOCX_CODE_TRACEABILITY_MATRIX_V10.md",
    ROOT / "docs" / "doctrine" / "DOCX_CODE_TRACEABILITY_MATRIX_V9.md",
    ROOT / "docs" / "doctrine" / "DOCX_CODE_TRACEABILITY_MATRIX_V8.md",
    ROOT / "docs" / "doctrine" / "DOCX_CODE_TRACEABILITY_MATRIX_V6.md",
    ROOT / "docs" / "doctrine" / "DOCX_CODE_TRACEABILITY_MATRIX_V5.md",
    ROOT / "docs" / "doctrine" / "DOCX_CODE_TRACEABILITY_MATRIX_V4.md",
    ROOT / "docs" / "doctrine" / "DOCX_CODE_TRACEABILITY_MATRIX_V3.md",
]

if not DOCX_DIR.exists():
    print("FAIL: Docx directory is missing")
    sys.exit(1)

matrix = next((p for p in MATRIX_CANDIDATES if p.exists()), None)
if matrix is None:
    print("FAIL: no V10/V9/V8/V6/V5/V4/V3 traceability matrix file is present")
    sys.exit(1)

matrix_text = matrix.read_text(encoding="utf-8")
missing: list[str] = []
for path in sorted(
    p for p in DOCX_DIR.iterdir()
    if p.is_file() and p.name not in {"extract.js", "extract_docs.py", "extract_specific.py"}
):
    if path.name not in matrix_text:
        missing.append(path.name)

if missing:
    print(f"FAIL: some Docx documentary files are not mapped in {matrix.name}")
    for item in missing:
        print(item)
    sys.exit(1)

print(f"PASS: every documentary-cycle file in Docx is mapped in {matrix.name}")
