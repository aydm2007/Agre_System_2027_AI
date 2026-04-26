#!/usr/bin/env python3
"""
[AGRI-GUARDIAN V21] Pre-commit Financial Safety Guard
=====================================================
Scans Python files in financial paths for:
1. float() usage in monetary context (must use Decimal)
2. Hardcoded credentials (passwords, tokens, secrets)
3. Direct ledger writes from non-service-layer code

Usage:
    python scripts/precommit_financial_guard.py
    
Exit codes:
    0 = clean
    1 = violations found
"""
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
FINANCE_PATHS = [
    BACKEND / "smart_agri" / "finance",
    BACKEND / "smart_agri" / "core" / "services",
    BACKEND / "smart_agri" / "core" / "models",
]
EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules", "migrations"}

FLOAT_PATTERN = re.compile(r"\bfloat\s*\(", re.IGNORECASE)
CRED_PATTERNS = [
    re.compile(r"""(password|secret|token|api_key)\s*=\s*['"][^'"]+['"]""", re.IGNORECASE),
]
DIRECT_LEDGER_PATTERN = re.compile(
    r"FinancialLedger\.objects\.(create|update|delete|bulk_create)", re.IGNORECASE
)

# These files are allowed to write to FinancialLedger (service layer)
SERVICE_ALLOWLIST = {
    "costing_service.py",
    "financial_integrity_service.py",
    "ledger_sync_service.py",
    "ledger_reversal_service.py",
    "fuel_reconciliation_posting_service.py",
}


def scan_file(filepath: Path) -> list[str]:
    violations = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return violations

    for i, line in enumerate(text.splitlines(), 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        # 1. float() in financial context
        if FLOAT_PATTERN.search(line):
            # Allow float() in non-financial contexts (e.g., test helpers)
            if "test" not in filepath.stem.lower():
                violations.append(f"  FLOAT: {filepath.name}:{i} — {stripped[:80]}")

        # 2. Hardcoded credentials
        for pat in CRED_PATTERNS:
            if pat.search(line):
                # Exclude test fixtures and Django settings defaults
                if "test" not in filepath.stem.lower() and "fixture" not in filepath.stem.lower():
                    violations.append(f"  CRED: {filepath.name}:{i} — {stripped[:80]}")

        # 3. Direct ledger writes outside service layer
        if DIRECT_LEDGER_PATTERN.search(line) and filepath.name not in SERVICE_ALLOWLIST:
            violations.append(f"  LEDGER: {filepath.name}:{i} — {stripped[:80]}")

    return violations


def main():
    all_violations = []
    for base in FINANCE_PATHS:
        if not base.exists():
            continue
        for py_file in base.rglob("*.py"):
            if any(d in py_file.parts for d in EXCLUDE_DIRS):
                continue
            vs = scan_file(py_file)
            all_violations.extend(vs)

    if all_violations:
        print(f"🔴 [AGRI-GUARDIAN] {len(all_violations)} financial safety violation(s) found:\n")
        for v in all_violations:
            print(v)
        print(f"\n--- Total: {len(all_violations)} violations ---")
        sys.exit(1)
    else:
        print("✅ [AGRI-GUARDIAN] Financial safety check passed — 0 violations.")
        sys.exit(0)


if __name__ == "__main__":
    main()
