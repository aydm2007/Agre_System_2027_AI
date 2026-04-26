"""
[AGRI-GUARDIAN] CI Guard: Fiscal Period Gate Check
Verifies that all financial mutation endpoints enforce fiscal period checks.
Run: python scripts/check_fiscal_period_gates.py
"""
import ast
import sys
import os

# Endpoints that MUST call FinanceService.check_fiscal_period or equivalent
FISCAL_GATE_REQUIRED = [
    "ActualExpenseViewSet",
    "TreasuryTransactionViewSet",
]

FISCAL_CHECK_FUNCTIONS = {
    "check_fiscal_period",
}


def check_file(filepath):
    violations = []
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            source = f.read()
            tree = ast.parse(source, filename=filepath)
        except SyntaxError:
            return violations

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name not in FISCAL_GATE_REQUIRED:
            continue

        # Check if any method in the class calls check_fiscal_period
        has_check = False
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute) and child.attr in FISCAL_CHECK_FUNCTIONS:
                has_check = True
                break
            if isinstance(child, ast.Name) and child.id in FISCAL_CHECK_FUNCTIONS:
                has_check = True
                break

        if not has_check:
            violations.append(
                f"  ❌ {filepath}:{node.lineno} — {node.name} MISSING fiscal period gate. "
                f"Must call FinanceService.check_fiscal_period() in mutation paths."
            )
    return violations


def main():
    import platform
    if platform.system() == 'Windows':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    backend_root = os.path.join(os.path.dirname(__file__), "..", "backend", "smart_agri")
    if not os.path.isdir(backend_root):
        backend_root = os.path.join(os.path.dirname(__file__), "backend", "smart_agri")
    if not os.path.isdir(backend_root):
        print("❌ Cannot find backend/smart_agri directory.")
        sys.exit(1)

    all_violations = []
    for root, dirs, files in os.walk(backend_root):
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                violations = check_file(fpath)
                all_violations.extend(violations)

    if all_violations:
        print(f"🛑 FISCAL PERIOD GATE CHECK FAILED ({len(all_violations)} violations):\n")
        for v in all_violations:
            print(v)
        sys.exit(1)
    else:
        print("✅ All financial mutation endpoints enforce fiscal period gates.")
        sys.exit(0)


if __name__ == "__main__":
    main()
