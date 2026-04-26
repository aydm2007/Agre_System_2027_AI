#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
required_files = [
    ROOT / 'docs' / 'doctrine' / 'ENTERPRISE_FULL_ROADMAP_V6.md',
    ROOT / 'docs' / 'doctrine' / 'MULTI_SITE_OFFLINE_OPERATIONS_V6.md',
    ROOT / 'docs' / 'doctrine' / 'ADMIN_DELEGATION_AND_APPROVALS_V6.md',
    ROOT / 'docs' / 'doctrine' / 'ARABIC_EXECUTIVE_REPORTING_V6.md',
    ROOT / 'docs' / 'doctrine' / 'DOCX_CODE_TRACEABILITY_MATRIX_V6.md',
    ROOT / 'docs' / 'doctrine' / 'V6_COMPLETION_READINESS.md',
    ROOT / 'docs' / 'operations' / 'ENTERPRISE_OPERATIONS_AR_V6.md',
    ROOT / 'docs' / 'operations' / 'ROLLBACK_AND_DR_AR_V6.md',
]
missing = [str(p.relative_to(ROOT)) for p in required_files if not p.exists()]
if missing:
    print('FAIL: V6 expansion artifacts missing')
    print('\n'.join(missing))
    sys.exit(1)
print('PASS: V6 expansion roadmap artifacts present')
