#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs' / 'reports' / 'GLOBAL_READINESS_EVIDENCE_2026-03-15_V7.md'

CHECKS = [
    ('verify-v6-static', ['make', 'verify-v6-static']),
    ('verify-v7-fixed-assets-and-fuel', ['python', 'scripts/verification/check_v7_fixed_assets_and_fuel.py']),
]

IMPORTANT_FILES = [
    'AGENTS.md',
    'docs/doctrine/STRICT_COMPLETION_MATRIX.md',
    'docs/doctrine/DUAL_MODE_OPERATIONAL_CYCLES.md',
    'docs/doctrine/V7_CLOSURE_NOTES.md',
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def run_check(name: str, cmd: list[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    except FileNotFoundError as e:
        return False, f'command missing: {e}'
    ok = proc.returncode == 0
    out = (proc.stdout or '') + (proc.stderr or '')
    out = out.strip()
    if len(out) > 6000:
        out = out[:6000] + '\n...truncated...'
    return ok, out


def main() -> int:
    rows = []
    all_ok = True
    for name, cmd in CHECKS:
        ok, output = run_check(name, cmd)
        rows.append((name, ok, output))
        all_ok = all_ok and ok

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', encoding='utf-8') as f:
        f.write('# GLOBAL READINESS EVIDENCE — V7\n\n')
        f.write(f'- Generated: {ts} (UTC)\n')
        f.write(f'- Root: `{ROOT}`\n')
        f.write(f'- Status: {"PASS" if all_ok else "PARTIAL"}\n\n')

        f.write('## Static gates\n\n')
        for name, ok, output in rows:
            f.write(f'### {name}: {"PASS" if ok else "FAIL"}\n\n')
            if output:
                f.write('```\n')
                f.write(output)
                f.write('\n```\n\n')

        f.write('## Integrity hashes (sha256)\n\n')
        for rel in IMPORTANT_FILES:
            p = ROOT / rel
            if p.exists():
                f.write(f'- `{rel}`: `{sha256_file(p)}`\n')
            else:
                f.write(f'- `{rel}`: MISSING\n')

        f.write('\n## Notes\n')
        f.write('- هذه وثيقة Evidence للبوابات الثابتة.\n')
        f.write('- الوصول إلى 100/100 نهائيًا ما يزال يتطلب أدلة runtime (Django/DB/Frontend tests).\n')

    print(f'WROTE: {OUT}')
    return 0 if all_ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
