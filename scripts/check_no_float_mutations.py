#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRONG_GATE = ROOT / 'backend' / 'scripts' / 'check_no_float_mutations.py'


def main() -> int:
    proc = subprocess.run([sys.executable, str(STRONG_GATE)], cwd=ROOT)
    return proc.returncode


if __name__ == '__main__':
    raise SystemExit(main())
