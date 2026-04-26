"""Stream seed_full_system output to file in real-time using environment-provided PostgreSQL settings."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = Path(str(os.getenv('AGRIASSET_SEED_OUTPUT', ROOT / 'seed_output.txt')))


def main():
    env = os.environ.copy()
    if not env.get('DB_PASSWORD'):
        raise SystemExit('DB_PASSWORD is required')
    env.setdefault('DB_USER', 'postgres')
    env.setdefault('DB_HOST', 'localhost')
    env.setdefault('DB_PORT', '5432')
    env.setdefault('DB_NAME', 'agriasset')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open('w', encoding='utf-8') as f:
        proc = subprocess.Popen([sys.executable, 'manage.py', 'seed_full_system', '--verbose'], cwd=str(ROOT), stdout=f, stderr=subprocess.STDOUT, env=env)
        proc.wait(timeout=240)
    print(f'DONE: exit={proc.returncode} output={OUTPUT}')


if __name__ == '__main__':
    main()
