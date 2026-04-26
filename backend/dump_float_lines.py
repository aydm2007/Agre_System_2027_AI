#!/usr/bin/env python3
"""Scan the repository for risky float usage.

Why:
- Financial / stock logic must use Decimal/exact arithmetic.
- This script is used as a forensic helper during audits.

Usage:
  python backend/dump_float_lines.py

Exit code:
  0 if no suspicious float usage found
  2 if suspicious float usage found
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
SCAN_ROOT = ROOT / "smart_agri"

EXCLUDE_DIRS = {"migrations", "tests", "__pycache__", "node_modules"}
EXCLUDE_FILES = {"settings.py"}  # settings may contain non-financial floats (timeouts etc.)

# Heuristics:
# - float(...) casts
# - numeric literals with a dot (e.g., 0.1) outside quotes
# - division with "/" without Decimal wrapping is also risky; we show it as advisory
RE_FLOAT_CALL = re.compile(r"\bfloat\s*\(")
RE_FLOAT_LITERAL = re.compile(r"(?<![\w'\"])\b\d+\.\d+\b")  # naive but effective
RE_DIVISION = re.compile(r"\b\w+\s*/\s*\w+")

def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if any(d in parts for d in EXCLUDE_DIRS):
        return True
    if path.name in EXCLUDE_FILES:
        return True
    return False

def scan_file(path: Path) -> list[tuple[int, str, str]]:
    findings = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return findings
    for idx, line in enumerate(lines, start=1):
        if "Decimal(" in line and "'" in line:
            # common safe pattern: Decimal('1.23')
            pass
        if RE_FLOAT_CALL.search(line):
            findings.append((idx, "float_call", line.strip()))
        # Ignore literals inside Decimal('...') strings by stripping quoted content naively
        stripped = re.sub(r"'[^']*'|\"[^\"]*\"", "\"\"", line)
        if RE_FLOAT_LITERAL.search(stripped):
            findings.append((idx, "float_literal", line.strip()))
    return findings

def main() -> int:
    all_findings = []
    for path in SCAN_ROOT.rglob("*.py"):
        if should_skip(path):
            continue
        f = scan_file(path)
        if f:
            for (ln, kind, text) in f:
                all_findings.append((path, ln, kind, text))

    if not all_findings:
        print("PASS: no suspicious float usage found in smart_agri/")
        return 0

    print("FAIL: suspicious float usage found (review and replace with Decimal)\n")
    for path, ln, kind, text in sorted(all_findings, key=lambda x: (str(x[0]), x[1], x[2])):
        rel = path.relative_to(ROOT)
        print(f"{rel}:{ln} [{kind}] {text}")

    print(f"\nTotal findings: {len(all_findings)}")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
