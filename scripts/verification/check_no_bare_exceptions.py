#!/usr/bin/env python
"""
[AGRI-GUARDIAN] CI Guardrail: Check for bare 'except Exception' in production code.

This script scans all Python files under backend/smart_agri/ (excluding tests
and migrations) for generic 'except Exception' catches, which violate the
AGENTS.md protocol: "Never generic Exception".

Exit code 0 = PASS (no bare exceptions found)
Exit code 1 = FAIL (bare exceptions detected)
"""
import os
import re
import sys

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'smart_agri')
PATTERN = re.compile(r'except\s+Exception[\s:(]')

# Directories/files to SKIP
SKIP_DIRS = {'tests', 'migrations', '__pycache__', 'management'}
SKIP_FILES = {'check_syntax.py'}  # utility scripts may legitimately catch broad errors

def scan_file(filepath):
    """Return list of (line_number, line_content) tuples with violations."""
    violations = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                # Skip commented lines
                if stripped.startswith('#'):
                    continue
                if PATTERN.search(line):
                    violations.append((i, stripped))
    except (OSError, UnicodeDecodeError):
        pass
    return violations


def main():
    base = os.path.normpath(os.path.abspath(BACKEND_DIR))
    if not os.path.isdir(base):
        print(f"ERROR: Directory not found: {base}")
        sys.exit(2)

    total_violations = 0
    files_with_violations = []

    for root, dirs, files in os.walk(base):
        # Prune directories we don't want to scan
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in files:
            if not fname.endswith('.py'):
                continue
            if fname in SKIP_FILES:
                continue

            fpath = os.path.join(root, fname)
            violations = scan_file(fpath)
            if violations:
                rel = os.path.relpath(fpath, base)
                files_with_violations.append(rel)
                for line_no, content in violations:
                    print(f"  VIOLATION: {rel}:{line_no} -> {content}")
                    total_violations += 1

    print()
    if total_violations == 0:
        print("✅ PASS: No bare 'except Exception' found in production code.")
        sys.exit(0)
    else:
        print(f"❌ FAIL: {total_violations} bare 'except Exception' found in {len(files_with_violations)} file(s).")
        print("   Fix: Replace with specific exception types per AGENTS.md protocol.")
        sys.exit(1)


if __name__ == '__main__':
    main()
