#!/usr/bin/env python3
"""Static bootstrap contract: required runtime files must exist and be referenced."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
required = [
    ROOT / "docker-compose.yml",
    ROOT / "docker-compose.prod.yml",
    ROOT / "backend" / "requirements.txt",
    ROOT / "backend" / "requirements-dev.txt",
    ROOT / "backend" / "Dockerfile",
    ROOT / "backend" / ".env.example",
    ROOT / "frontend" / "package.json",
    ROOT / "frontend" / "package-lock.json",
    ROOT / "README_Install.md",
    ROOT / "START_HERE.md",
    ROOT / "Makefile",
]
missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
if missing:
    print("FAIL: bootstrap/runtime contract missing required files")
    for item in missing:
        print(item)
    sys.exit(1)

print("PASS: bootstrap/runtime contract files are present")
