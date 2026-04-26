#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs' / 'reports' / 'GLOBAL_READINESS_EVIDENCE_2026-03-15_V8.md'
CHECKS = [
    ('verify-v8-static', ['make', 'verify-v8-static']),
    ('strong-float-gate', [sys.executable, 'backend/scripts/check_no_float_mutations.py']),
]
IMPORTANT_FILES = [
    'AGENTS.md',
    'docs/doctrine/V8_FINAL_CLOSURE_MATRIX.md',
    'docs/doctrine/DOCX_CODE_TRACEABILITY_MATRIX_V8.md',
    'docs/reports/REMEDIATION_REGISTER_V8.md',
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def run_check(name: str, cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = ((proc.stdout or '') + (proc.stderr or '')).strip()
    if len(out) > 8000:
        out = out[:8000] + '\n...truncated...'
    return proc.returncode == 0, out


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
        f.write('# GLOBAL READINESS EVIDENCE — V8\n\n')
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
            f.write(f'- `{rel}`: `{sha256_file(p) if p.exists() else "MISSING"}`\n')
        f.write('\n## Notes\n')
        f.write('- تم توليد الدليل باستخدام البوابة القوية للـ float فقط لتجنب أي drift.\n')
        f.write('- 100/100 النهائي ما يزال يتطلب أدلة runtime (Django/DB/Frontend tests).\n')
    print(f'WROTE: {OUT}')
    return 0 if all_ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
