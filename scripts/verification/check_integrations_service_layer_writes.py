#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'backend' / 'smart_agri' / 'integrations' / 'api.py'
PATTERNS = [
    re.compile(r"serializer\.save\s*\("),
    re.compile(r"[A-Za-z_][A-Za-z0-9_]*\.save\s*\("),
    re.compile(r"[A-Za-z_][A-Za-z0-9_]*\.delete\s*\("),
    re.compile(r"[A-Za-z_][A-Za-z0-9_]*\.objects\.create\s*\("),
]
ALLOW = {"ExternalFinanceBatchService.", "self._commit_action_idempotency(", "self._enforce_action_idempotency("}
violations = []
for lineno, line in enumerate(TARGET.read_text(encoding='utf-8').splitlines(), start=1):
    stripped = line.strip()
    if any(token in stripped for token in ALLOW):
        continue
    for pattern in PATTERNS:
        if pattern.search(stripped):
            violations.append(f"{TARGET.relative_to(ROOT)}:{lineno}: {stripped}")
            break
if violations:
    print('FAIL: direct write patterns found in integrations/api.py')
    for item in violations:
        print(item)
    sys.exit(1)
print('PASS: integrations/api.py delegates governed writes to services')
