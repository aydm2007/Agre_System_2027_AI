#!/usr/bin/env python3
"""Fail if finance API modules write directly instead of delegating to services."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FINANCE_DIR = ROOT / "backend" / "smart_agri" / "finance"
TARGETS = sorted(FINANCE_DIR.glob("api_*.py"))

PATTERNS = [
    re.compile(r"\bserializer\.save\s*\("),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.objects\.create\s*\("),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.save\s*\("),
]

ALLOW_SUBSTRINGS = {
    "self._log_action(",
    "self._commit_action_idempotency(",
    "self._enforce_action_idempotency(",
    "IdempotencyService.commit_",
}

violations: list[str] = []
for path in TARGETS:
    lines = path.read_text(encoding="utf-8").splitlines()
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if any(token in stripped for token in ALLOW_SUBSTRINGS):
            continue
        for pattern in PATTERNS:
            if pattern.search(stripped):
                violations.append(f"{path.relative_to(ROOT)}:{lineno}: {stripped}")
                break

if violations:
    print("FAIL: direct write patterns found in finance API modules")
    for item in violations:
        print(item)
    sys.exit(1)

print("PASS: finance API modules delegate governed writes to services")
