#!/usr/bin/env python3
"""Enterprise readiness static contract for V4 candidate."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
required_files = [
    ROOT / '.env.enterprise.example',
    ROOT / 'docker-compose.enterprise.yml',
    ROOT / 'docs' / 'operations' / 'ENTERPRISE_PRODUCTION_RUNBOOK_V4.md',
    ROOT / 'docs' / 'operations' / 'BACKUP_RESTORE_RUNBOOK_V4.md',
    ROOT / 'docs' / 'operations' / 'OBSERVABILITY_AND_SECURITY_BASELINE_V4.md',
    ROOT / 'docs' / 'doctrine' / 'ENTERPRISE_PRODUCTION_PLAN_V4.md',
    ROOT / 'docs' / 'doctrine' / 'V4_COMPLETION_READINESS.md',
    ROOT / 'scripts' / 'ops' / 'pg_backup_custom.sh',
    ROOT / 'scripts' / 'ops' / 'pg_restore_custom.sh',
    ROOT / 'scripts' / 'ops' / 'preflight_enterprise.sh',
]
missing = [str(p.relative_to(ROOT)) for p in required_files if not p.exists()]
if missing:
    print('FAIL: enterprise readiness missing required artifacts')
    for item in missing:
        print(item)
    sys.exit(1)

compose_text = (ROOT / 'docker-compose.prod.yml').read_text(encoding='utf-8')
for needle in ['healthcheck:', 'restart: unless-stopped', 'condition: service_healthy']:
    if needle not in compose_text:
        print(f'FAIL: docker-compose.prod.yml missing enterprise marker: {needle}')
        sys.exit(1)

env_text = (ROOT / '.env.enterprise.example').read_text(encoding='utf-8')
for key in ['DJANGO_SECRET_KEY', 'SECURE_SSL_REDIRECT', 'BACKUP_RETENTION_DAYS', 'APP_REQUIRE_VERSION_HEADER']:
    if re.search(rf'^{re.escape(key)}=', env_text, flags=re.M) is None:
        print(f'FAIL: .env.enterprise.example missing {key}')
        sys.exit(1)

make_text = (ROOT / 'Makefile').read_text(encoding='utf-8')
for target in ['verify-enterprise-static', 'ops-preflight', 'backup-db-custom', 'restore-db-custom']:
    if re.search(rf'^{re.escape(target)}:', make_text, flags=re.M) is None:
        print(f'FAIL: Makefile missing target {target}')
        sys.exit(1)

print('PASS: enterprise readiness static contract is present for V4 candidate')
