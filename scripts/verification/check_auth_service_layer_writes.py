#!/usr/bin/env python3
"""Fail if auth API modules mutate users/groups directly instead of delegating to services."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "backend" / "smart_agri" / "accounts" / "api_auth.py"

PATTERNS = [
    re.compile(r"\bserializer\.save\s*\("),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.save\s*\("),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.delete\s*\("),
    re.compile(r"\buser_permissions\.(add|remove)\s*\("),
    re.compile(r"\bgroups\.(add|remove|set)\s*\("),
    re.compile(r"\bpermissions\.(add|remove|set)\s*\("),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.objects\.create\s*\("),
]

ALLOW_SUBSTRINGS = {
    "UserWriteService.",
    "GroupWriteService.",
}

violations: list[str] = []
for lineno, line in enumerate(TARGET.read_text(encoding="utf-8").splitlines(), start=1):
    stripped = line.strip()
    if any(token in stripped for token in ALLOW_SUBSTRINGS):
        continue
    for pattern in PATTERNS:
        if pattern.search(stripped):
            violations.append(f"{TARGET.relative_to(ROOT)}:{lineno}: {stripped}")
            break

if violations:
    print("FAIL: direct write patterns found in accounts/api_auth.py")
    for item in violations:
        print(item)
    sys.exit(1)

print("PASS: accounts/api_auth.py delegates governed writes to services")
