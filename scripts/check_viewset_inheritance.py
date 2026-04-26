"""
[AGRI-GUARDIAN] CI Guard: ViewSet Inheritance Check
Ensures all core ViewSets inherit from AuditedModelViewSet (not bare ModelViewSet).
Run: python scripts/check_viewset_inheritance.py
"""
import ast
import sys
import os

REQUIRED_BASE_CLASSES = {"AuditedModelViewSet"}
EXCLUDED_VIEWSETS = {
    "AuditedModelViewSet",  # Base class, not an endpoint
    "FinancialLedgerViewSet",  # ReadOnlyModelViewSet by design
    "AuditLogViewSet",  # ReadOnlyModelViewSet by design
    "PermissionViewSet",  # Django auth model, ReadOnly
    "CashBoxViewSet",  # ReadOnlyModelViewSet by design
    "UserViewSet",  # Django auth model
    "GroupViewSet",  # Django auth model
}


def check_file(filepath):
    violations = []
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return violations

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name.endswith("ViewSet"):
            continue
        if node.name in EXCLUDED_VIEWSETS:
            continue

        base_names = set()
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_names.add(base.id)
            elif isinstance(base, ast.Attribute):
                base_names.add(base.attr)

        bare_modelviewset = "ModelViewSet" in base_names and not base_names & REQUIRED_BASE_CLASSES
        if bare_modelviewset:
            violations.append(
                f"  ❌ {filepath}:{node.lineno} — {node.name} uses bare ModelViewSet. "
                f"Must inherit from AuditedModelViewSet."
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
        print(f"🛑 VIEWSET INHERITANCE CHECK FAILED ({len(all_violations)} violations):\n")
        for v in all_violations:
            print(v)
        sys.exit(1)
    else:
        print("✅ All ViewSets correctly inherit from AuditedModelViewSet.")
        sys.exit(0)


if __name__ == "__main__":
    main()
