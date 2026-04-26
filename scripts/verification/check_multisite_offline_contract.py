#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
py = ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'multi_site_policy_service.py'
doc = ROOT / 'docs' / 'doctrine' / 'MULTI_SITE_OFFLINE_OPERATIONS_V6.md'
if not py.exists() or not doc.exists():
    print('FAIL: multi-site offline artifacts missing')
    sys.exit(1)
text = py.read_text(encoding='utf-8')
for needle in ['class OperationScope', 'sector_id', 'site_id', 'offline_enabled', 'sync_strategy']:
    if needle not in text:
        print(f'FAIL: multi-site policy missing {needle}')
        sys.exit(1)
print('PASS: V6 multi-site offline contract present')
