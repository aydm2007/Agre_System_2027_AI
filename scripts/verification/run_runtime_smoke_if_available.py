from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'backend'


def main() -> int:
    if importlib.util.find_spec('django') is None:
        print('SKIP: Django is not installed in this environment; runtime smoke not executed.')
        return 0
    env = os.environ.copy()
    env.setdefault('PYTHONPATH', str(BACKEND))
    commands = [
        ['python', str(BACKEND / 'manage.py'), 'check'],
    ]
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=str(BACKEND), env=env, check=False)
        if proc.returncode != 0:
            return proc.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
