#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'audit_event_factory.py'
if not path.exists():
    print('FAIL: audit_event_factory.py missing')
    sys.exit(1)
text = path.read_text(encoding='utf-8')
required = ['class AuditEvent', 'class AuditEventFactory', 'def build(', 'def record(', 'reason', 'farm_id', 'mode']
for needle in required:
    if needle not in text:
        print(f'FAIL: audit event factory missing {needle}')
        sys.exit(1)
print('PASS: V6 audit event factory contract present')
