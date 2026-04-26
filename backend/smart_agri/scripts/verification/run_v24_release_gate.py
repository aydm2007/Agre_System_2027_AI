from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND = REPO_ROOT / 'backend'
FRONTEND = REPO_ROOT / 'frontend'
PYTHON = sys.executable

def run(cmd, *, cwd, env=None):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(cmd, cwd=cwd, env=merged, text=True, capture_output=True)
    return {
        'cmd': ' '.join(cmd),
        'cwd': str(cwd),
        'returncode': proc.returncode,
        'stdout': proc.stdout[-8000:],
        'stderr': proc.stderr[-8000:],
    }

def main() -> int:
    checks = []
    checks.append(run([PYTHON, 'manage.py', 'check'], cwd=BACKEND))
    checks.append(run([PYTHON, 'manage.py', 'check', '--deploy'], cwd=BACKEND))
    checks.append(run([PYTHON, 'scripts/check_no_float_mutations.py'], cwd=BACKEND))
    checks.append(run([PYTHON, 'scripts/check_idempotency_actions.py'], cwd=BACKEND))
    checks.append(run([PYTHON, str(REPO_ROOT / 'scripts' / 'check_farm_scope_guards.py')], cwd=REPO_ROOT))
    sqlite_env = {
        'DJANGO_SETTINGS_MODULE': 'smart_agri.test_settings_sqlite',
        'DJANGO_DEBUG': 'True',
        'APP_REQUIRE_VERSION_HEADER': 'False',
    }
    checks.append(run([PYTHON, 'manage.py', 'test',
        'smart_agri.finance.tests.test_approval_workflow_api',
        'smart_agri.finance.tests.test_approval_override_and_reopen',
        'smart_agri.finance.tests.test_v15_profiled_posting_authority',
        'smart_agri.core.tests.test_attachment_policy_service',
        'smart_agri.core.tests.test_v18_remote_review_reporting',
        'smart_agri.core.tests.test_v19_remote_review_snapshot',
        'smart_agri.core.tests.test_v20_attachment_lifecycle',
        '--noinput', '-v', '2'], cwd=BACKEND, env=sqlite_env))
    # PostgreSQL-specific checks remain honest when unavailable
    for rel in ['scripts/verification/detect_zombies.py', 'scripts/verification/detect_ghost_triggers.py']:
        path = BACKEND / rel
        if path.exists():
            checks.append(run([PYTHON, rel], cwd=BACKEND))
    frontend_script = FRONTEND / 'tests' / 'static_mode_access_v24.mjs'
    if frontend_script.exists():
        checks.append(run(['node', str(frontend_script)], cwd=FRONTEND))
    report = {
        'version': 'V24',
        'summary': {
            'pass': sum(1 for c in checks if c['returncode'] == 0),
            'blocked_or_failed': sum(1 for c in checks if c['returncode'] != 0),
        },
        'checks': checks,
    }
    out = REPO_ROOT / 'AGRIASSET_V24_RELEASE_GATE_REPORT.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['summary']['blocked_or_failed'] == 0 else 1

if __name__ == '__main__':
    raise SystemExit(main())
