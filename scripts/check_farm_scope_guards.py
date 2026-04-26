import re
import sys
import json
from pathlib import Path
from datetime import date


ROOT = Path("backend/smart_agri")
EXCLUDED_PARTS = ("/tests/", "\\tests\\", "/migrations/", "\\migrations\\")

EXCEPTIONS_FILE = Path("scripts/farm_scope_exceptions.json")

CLASS_RE = re.compile(
    r"class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\((?P<bases>[^)]*ViewSet[^)]*)\):\n(?P<body>(?:[ \t]+.*\n|\n)*)",
    re.MULTILINE,
)

TENANT_GUARD_TOKENS = (
    "user_farm_ids(",
    "_limit_queryset_to_user_farms(",
    "_ensure_user_has_farm_access(",
    "farm_id__in=",
    "location__farm_id__in=",
    "employee__farm_id__in=",
)

MUTATION_METHODS = ("def create(", "def perform_create(", "def perform_update(", "def perform_destroy(")


def iter_py_files():
    for file_path in ROOT.rglob("*.py"):
        file_text = str(file_path)
        if any(part in file_text for part in EXCLUDED_PARTS):
            continue
        yield file_path


def has_guard(content: str) -> bool:
    return any(token in content for token in TENANT_GUARD_TOKENS)


def looks_business_viewset(bases: str) -> bool:
    # Limit to mutable model-backed viewsets.
    return ("ModelViewSet" in bases) or ("AuditedModelViewSet" in bases)


def main() -> int:
    if not EXCEPTIONS_FILE.exists():
        print(f"Missing exceptions file: {EXCEPTIONS_FILE}")
        return 1

    try:
        exceptions = json.loads(EXCEPTIONS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Invalid exceptions JSON: {exc}")
        return 1

    # Enforce documented reason and expiry review date for each exemption.
    for class_name, meta in exceptions.items():
        if not isinstance(meta, dict) or not str(meta.get("reason", "")).strip():
            print(f"Exception entry missing reason: {class_name}")
            return 1
        review_due = str(meta.get("review_due", "")).strip()
        if not review_due:
            print(f"Exception entry missing review_due: {class_name}")
            return 1
        try:
            due = date.fromisoformat(review_due)
        except ValueError:
            print(f"Invalid review_due format (YYYY-MM-DD required): {class_name}={review_due}")
            return 1
        if due < date.today():
            print(f"Expired exception review_due: {class_name}={review_due}")
            return 1

    exempt_classes = set(exceptions.keys())
    violations = []
    scanned = 0

    for file_path in iter_py_files():
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for match in CLASS_RE.finditer(content):
            class_name = match.group("name")
            bases = match.group("bases")
            body = match.group("body")

            if class_name in exempt_classes:
                continue
            if not looks_business_viewset(bases):
                continue
            if not any(method in body for method in MUTATION_METHODS):
                continue

            scanned += 1
            if not has_guard(body):
                violations.append(f"{file_path}:{class_name}")

    if violations:
        print("Farm-scope guard missing in mutable business viewsets:")
        for item in violations:
            print(f" - {item}")
        return 1

    print(
        f"Farm-scope guard check passed. viewsets_scanned={scanned} exceptions={len(exempt_classes)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
