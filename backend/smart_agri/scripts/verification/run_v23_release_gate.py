"""Local evidence gate for V23.

Runs the safest verifications available in constrained environments:
- Django system checks
- optional PostgreSQL-aware zombie/trigger detectors
- targeted governance tests on SQLite test settings

This script is intentionally honest: missing PostgreSQL becomes BLOCKED, not PASS.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / 'backend'
PYTHON = sys.executable


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> dict:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(
        cmd,
        cwd=BACKEND,
        env=merged,
        text=True,
        capture_output=True,
    )
    return {
        'cmd': ' '.join(cmd),
        'returncode': proc.returncode,
        'stdout': proc.stdout[-6000:],
        'stderr': proc.stderr[-6000:],
    }


def main() -> int:
    checks = []
    checks.append(run([PYTHON, 'manage.py', 'check']))
    checks.append(run([PYTHON, 'manage.py', 'check', '--deploy']))

    postgres_checks = [
        ['scripts/verification/detect_zombies.py'],
        ['scripts/verification/detect_ghost_triggers.py'],
    ]
    for rel in postgres_checks:
        path = BACKEND / rel[0]
        if path.exists():
            checks.append(run([PYTHON, rel[0]]))

    sqlite_env = {
        'DJANGO_SETTINGS_MODULE': 'smart_agri.test_settings_sqlite',
        'DJANGO_DEBUG': 'True',
        'APP_REQUIRE_VERSION_HEADER': 'False',
    }
    checks.append(
        run(
            [
                PYTHON,
                'manage.py',
                'test',
                'smart_agri.finance.tests.test_approval_workflow_api',
                'smart_agri.finance.tests.test_approval_override_and_reopen',
                '--noinput',
                '-v',
                '2',
            ],
            env=sqlite_env,
        )
    )

    report = {
        'version': 'V23',
        'summary': {
            'pass': sum(1 for c in checks if c['returncode'] == 0),
            'blocked_or_failed': sum(1 for c in checks if c['returncode'] != 0),
        },
        'checks': checks,
    }
    out = REPO_ROOT / 'AGRIASSET_V23_RELEASE_GATE_REPORT.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['summary']['blocked_or_failed'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
