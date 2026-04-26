#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
required = [ROOT/'docker-compose.postgres-bootstrap.yml', ROOT/'backend'/'.env.postgres.example', ROOT/'scripts'/'bootstrap'/'bootstrap_postgres_foundation.sh', ROOT/'backend'/'smart_agri'/'core'/'management'/'commands'/'bootstrap_postgres_foundation.py', ROOT/'docs'/'operations'/'POSTGRESQL_FOUNDATION_BOOTSTRAP_V38.md']
missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    print('FAIL: PostgreSQL foundation package missing required files')
    print('\n'.join(missing))
    sys.exit(1)
print('PASS: PostgreSQL foundation package files are present')
