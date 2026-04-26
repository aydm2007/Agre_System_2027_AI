import ast
import sys
from pathlib import Path


ROOTS = [
    Path("backend/smart_agri/finance"),
    Path("backend/smart_agri/sales"),
    Path("backend/smart_agri/inventory"),
    # Core viewsets contain operational mutations (logs, inventory actions, approvals).
    Path("backend/smart_agri/core/api/viewsets"),
    # Core API modules may expose mutation actions outside viewsets.
    Path("backend/smart_agri/core/api"),
]
EXCLUDED_PARTS = ("/tests/", "\\tests\\", "/migrations/", "\\migrations\\", "/serializers/", "\\serializers\\")
SKIP_ACTION_NAMES = {
    "summary",
    "day_summary",
    "tree_snapshot",
    "invoice",
    "defaults",
    "team_suggestions",
    "close",
}

MUTATION_METHODS = {
    # DRF endpoint actions only. (perform_* hooks are not HTTP endpoints)
    "create",
    "update",
    "partial_update",
    "destroy",
}


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _is_mutating_action(fn: ast.FunctionDef) -> bool:
    for dec in fn.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        target = dec.func.attr if isinstance(dec.func, ast.Attribute) else getattr(dec.func, "id", "")
        if target != "action":
            continue
        for kw in dec.keywords:
            if kw.arg != "methods":
                continue
            if isinstance(kw.value, (ast.List, ast.Tuple)):
                for item in kw.value.elts:
                    if isinstance(item, ast.Constant) and str(item.value).lower() in {"post", "patch", "delete"}:
                        return True
    return False


def _function_body_has_guard(content: str, fn: ast.FunctionDef) -> bool:
    if fn.end_lineno is None:
        return False
    lines = content.splitlines()
    start = max(fn.lineno - 1, 0)
    end = max(fn.end_lineno, start)
    block = "\n".join(lines[start:end])
    return (
        "_enforce_action_idempotency(" in block
        or "_transition_period_status(" in block
        or "resolve_farm_action_context(" in block
    )


def iter_target_files():
    for root in ROOTS:
        if not root.exists():
            continue
        for file_path in root.rglob("*.py"):
            file_text = str(file_path)
            if any(part in file_text for part in EXCLUDED_PARTS):
                continue
            yield file_path


def main() -> int:
    violations = []
    scanned = 0

    for file_path in iter_target_files():
        # Some Windows-edited files may include UTF-8 BOM.
        content = file_path.read_text(encoding="utf-8-sig")
        if "ViewSet" not in content:
            continue
        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            violations.append(f"{file_path}:syntax_error:{exc.lineno}")
            continue

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            base_names = {_base_name(base) for base in node.bases}
            if not any("ViewSet" in name for name in base_names):
                continue
            uses_audited_base = "AuditedModelViewSet" in base_names
            uses_idempotent_create_mixin = "IdempotentCreateMixin" in base_names
            # Keep this scanner aligned with "scoped financial mutation actions".
            if not (uses_audited_base or uses_idempotent_create_mixin):
                continue
            scanned += 1

            methods_to_check = set()
            for child in node.body:
                if not isinstance(child, ast.FunctionDef):
                    continue
                if child.name in MUTATION_METHODS or _is_mutating_action(child):
                    methods_to_check.add(child.name)

            for fn_name in methods_to_check:
                if fn_name in SKIP_ACTION_NAMES:
                    continue
                if uses_audited_base and fn_name in {
                    "create",
                    "update",
                    "partial_update",
                    "destroy",
                    "perform_create",
                    "perform_update",
                    "perform_destroy",
                }:
                    # Covered centrally by AuditedModelViewSet.
                    continue
                if uses_idempotent_create_mixin and fn_name in {"create", "perform_create"}:
                    # Covered by IdempotentCreateMixin create flow.
                    continue
                fn_nodes = [n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == fn_name]
                fn_node = fn_nodes[0] if fn_nodes else None
                if fn_node is None or not _function_body_has_guard(content, fn_node):
                    violations.append(f"{file_path}:{fn_name}")

    if scanned == 0:
        print("BLOCK: idempotency scanner covered zero ViewSet classes; verification is invalid.")
        return 1

    if violations:
        print("Idempotency guard missing in mutation actions (POST/PATCH/DELETE/create/update/destroy):")
        for item in violations:
            print(f" - {item}")
        return 1

    print(f"All scoped financial mutation actions include idempotency guard. classes_scanned={scanned}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
