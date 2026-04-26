#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
BANNED_FILES = [
    ROOT / 'BK_24_2_2026.sql',
    ROOT / 'agree_asset_v3_1.sql',
    ROOT / 'backend' / 'production_seed_v1.json',
    ROOT / 'backend' / 'wipe_direct.sql',
    ROOT / 'audit_results.log',
]
BANNED_LITERALS = ('Ibra3898@', 'admin_password', 'Guardian123!', 'mypassword')
SKIP_PARTS = {'tests', '__pycache__', 'node_modules', '.git'}
HISTORICAL_MARKERS = (
    'historical',
    'superseded',
    'dated context',
    'informative only',
    'verify_axis_complete_v21/summary.json',
)


def load_latest_axis_summary() -> dict:
    summary_path = (
        ROOT
        / 'docs'
        / 'evidence'
        / 'closure'
        / 'latest'
        / 'verify_axis_complete_v21'
        / 'summary.json'
    )
    try:
        return json.loads(summary_path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def latest_axis_is_live_pass(summary: dict) -> bool:
    return summary.get('overall_status') == 'PASS' and summary.get('axis_overall_status') == 'PASS'


def is_historical_or_template(path: Path, text: str) -> bool:
    if 'TEMPLATE' in path.name.upper():
        return True
    head = '\n'.join(text.splitlines()[:12]).lower()
    return any(marker in head for marker in HISTORICAL_MARKERS)


def scan_active_score_claims(summary: dict) -> list[str]:
    if latest_axis_is_live_pass(summary):
        return []

    violations: list[str] = []
    report_root = ROOT / 'docs' / 'reports'
    for path in sorted(report_root.rglob('*.md')):
        text = path.read_text(encoding='utf-8', errors='replace')
        if '100/100' not in text:
            continue
        if is_historical_or_template(path, text):
            continue
        violations.append(
            'active score claim contradicts latest canonical evidence: '
            f"{path.relative_to(ROOT)} (latest overall_status={summary.get('overall_status', 'missing')} "
            f"axis_overall_status={summary.get('axis_overall_status', 'missing')})"
        )
    return violations


def scan_prompt_precedence() -> list[str]:
    prompt_path = ROOT / 'docs' / 'reference' / 'CANONICAL_UNIFIED_PROMPT_V21.md'
    if not prompt_path.exists():
        return [f'missing canonical prompt scaffold: {prompt_path.relative_to(ROOT)}']

    text = prompt_path.read_text(encoding='utf-8', errors='replace')
    required_tokens = (
        'Execution scaffold only',
        '1. `docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md`',
        '2. أي `AGENTS.md` أعمق',
        '3. `AGENTS.md` في الروت',
        'REFERENCE_MANIFEST_V21.yaml',
        'REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md',
    )
    missing = [token for token in required_tokens if token not in text]
    if not missing:
        return []
    return [
        'canonical prompt scaffold missing precedence guard tokens: '
        f'{missing}'
    ]


def scan_banned_artifacts_and_literals() -> list[str]:
    violations: list[str] = []
    for path in BANNED_FILES:
        if path.exists():
            violations.append(f'banned artifact present: {path.relative_to(ROOT)}')
    allowed_suffixes = {'.py', '.js', '.jsx', '.ts', '.tsx', '.md', '.sh', '.yml', '.yaml', '.json'}
    for current_root, dir_names, file_names in os.walk(ROOT, topdown=True, onerror=lambda _err: None):
        dir_names[:] = [name for name in dir_names if name not in SKIP_PARTS]
        current_dir = Path(current_root)
        for file_name in file_names:
            path = current_dir / file_name
            if path == SELF or path.suffix.lower() not in allowed_suffixes:
                continue
            try:
                text = path.read_text(encoding='utf-8')
            except OSError:
                continue
            for literal in BANNED_LITERALS:
                if literal in text:
                    violations.append(f'hardcoded secret marker {literal!r} in {path.relative_to(ROOT)}')
    return violations


def main() -> int:
    violations = scan_banned_artifacts_and_literals()
    latest_axis_summary = load_latest_axis_summary()
    violations.extend(scan_active_score_claims(latest_axis_summary))
    violations.extend(scan_prompt_precedence())
    if violations:
        print('FAIL: release hygiene violations detected')
        for item in violations:
            print(item)
        return 1
    print('PASS: release hygiene static contract is clean')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
