#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path
from datetime import datetime
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
REPORT = ROOT / 'PHASE_0_TO_7_GATE_REPORT_2026-03-16.md'

PHASES = [
    (0, 'Baseline', [
        ['python', 'scripts/verification/check_bootstrap_contract.py'],
        ['python', 'scripts/verification/check_docx_traceability.py'],
        ['python', 'scripts/verification/check_compliance_docs.py'],
    ]),
    (1, 'Tenant Isolation', [
        ['python', 'scripts/check_farm_scope_guards.py'],
        ['python', 'scripts/verification/check_auth_service_layer_writes.py'],
    ]),
    (2, 'Idempotency', [
        ['python', 'scripts/check_idempotency_actions.py'],
    ]),
    (3, 'Decimal + Surra', [
        ['python', 'scripts/check_no_float_mutations.py'],
    ]),
    (4, 'Approval / Variance Governance', [
        ['python', 'backend/scripts/check_variance_controls.py'],
    ]),
    (5, 'Period Close & Audit', [
        ['python', 'backend/scripts/check_audit_trail_coverage.py'],
    ]),
    (6, 'Schema Hygiene', [
        ['python', 'scripts/verification/detect_zombies.py'],
        ['python', 'scripts/verification/detect_ghost_triggers.py'],
    ]),
    (7, 'Offline Immunity / Runtime Gate', [
        ['python', 'backend/manage.py', 'check'],
        ['python', 'scripts/verification/check_backup_freshness.py'],
        ['python', 'scripts/verification/check_restore_drill_evidence.py'],
    ]),
]


def classify(stdout: str, code: int) -> str:
    upper = stdout.upper()
    if code == 0 and 'FAIL' not in upper and 'BLOCKED' not in upper:
        return 'PASS'
    if 'BLOCKED' in upper:
        return 'BLOCKED'
    return 'FAIL'


def run(cmd: list[str]) -> tuple[str, str, int]:
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired as exc:
        return 'BLOCKED', f'timeout: {exc}', 124
    except FileNotFoundError as exc:
        return 'BLOCKED', f'missing executable: {exc}', 127
    out = ((proc.stdout or '') + ('\n' + proc.stderr if proc.stderr else '')).strip()
    return classify(out, proc.returncode), out, proc.returncode


def main() -> int:
    lines = [
        '# Phase 0 to Phase 7 Gate Report',
        '',
        f'Generated at: {datetime.now().isoformat(timespec="seconds")}',
        '',
        '| Phase | Name | Status | Notes |',
        '|---:|---|---|---|',
    ]
    worst = 'PASS'
    status_rank = {'PASS': 0, 'BLOCKED': 1, 'FAIL': 2}
    for phase, name, commands in PHASES:
        phase_status = 'PASS'
        notes = []
        for cmd in commands:
            status, output, code = run(cmd)
            if status_rank[status] > status_rank[phase_status]:
                phase_status = status
            first_line = output.splitlines()[0] if output else f'exit={code}'
            notes.append(f"`{' '.join(cmd)}` → {status} · {first_line[:120]}")
        if status_rank[phase_status] > status_rank[worst]:
            worst = phase_status
        lines.append(f'| {phase} | {name} | {phase_status} | ' + '<br>'.join(notes).replace('|', '\\|') + ' |')
    lines += [
        '',
        '## Summary',
        '',
        f'- Overall gate status: **{worst}**',
        '- PASS means the evidence available in this environment supports the phase.',
        '- BLOCKED means the phase requires a missing runtime dependency such as PostgreSQL or external evidence.',
        '- FAIL means a check executed and reported a broken contract.',
        '',
        '## Notes',
        '',
        '- This report is intentionally evidence-gated and does not convert BLOCKED into PASS.',
        '- PostgreSQL/RLS-specific checks may remain BLOCKED on environments without a live PostgreSQL service.',
    ]
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(REPORT)
    return 0 if worst == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
