#!/usr/bin/env python3
"""Fail if governed account APIs write directly instead of delegating to services."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    ROOT / "backend" / "smart_agri" / "accounts" / "api_governance.py",
    ROOT / "backend" / "smart_agri" / "accounts" / "api_membership.py",
]

PATTERNS = [
    re.compile(r"\bserializer\.save\s*\("),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.objects\.create\s*\("),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.save\s*\("),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.delete\s*\("),
]

ALLOW_SUBSTRINGS = {
    "GovernanceService.",
    "MembershipService.",
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
    print("FAIL: direct write patterns found in governed accounts API modules")
    for item in violations:
        print(item)
    sys.exit(1)

print("PASS: governed accounts API modules delegate writes to services")
