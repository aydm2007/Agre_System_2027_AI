"""
[AGRI-GUARDIAN] Idempotency Compliance Checker (v2 — Class-Level)
Release Gate: Axis 2 — Idempotency V2 & Offline Immunity

CRIT-02 FIX: Previous version used a file-level '@idempotent' search, which
produced false positives. This version extracts each class body individually
and verifies that the @idempotent tag is present within THAT specific class's
block only.

Rules (per AGENTS.md §Idempotency Standard):
- ViewSets that handle mutations (POST/PATCH/DELETE) MUST have @idempotent
  in their class docstring, OR inherit from FinancialMutationViewSet.
- Missing @idempotent on a mutation ViewSet = FAIL (release blocker).
"""
import os
import re
import sys

# Configuration
TARGET_APPS = [
    'backend/smart_agri/finance',
    'backend/smart_agri/inventory',
    'backend/smart_agri/sales',
]

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def extract_class_body(content: str, class_start_pos: int) -> str:
    """
    Extract the body of a class starting at class_start_pos.
    Stops when a new top-level class/def is found (dedented back to col 0).
    This gives a per-class view to avoid cross-class false positives.
    """
    lines = content[class_start_pos:].split('\n')
    body_lines = []
    in_class = False
    for line in lines:
        if not in_class:
            body_lines.append(line)
            in_class = True
            continue
        # A new top-level definition signals the end of this class
        if line and not line[0].isspace() and line.strip() and not line.strip().startswith('#'):
            break
        body_lines.append(line)
    return '\n'.join(body_lines)


def check_file(filepath: str) -> int:
    """
    Returns the count of hard errors (non-compliant non-readonly ViewSets).
    """
    errors = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"{YELLOW}[SKIP] Cannot read {filepath}: {e}{RESET}")
        return 0

    # Pattern: class ClassName(BaseClass[es]):
    view_pattern = re.compile(r'^class\s+(\w+)\s*\((.*?)\)\s*:', re.MULTILINE)

    for match in view_pattern.finditer(content):
        class_name = match.group(1)
        base_classes = match.group(2)

        # Only audit ViewSets / APIViews
        if 'ViewSet' not in base_classes and 'APIView' not in base_classes:
            continue

        # ReadOnly views don't mutate — skip
        is_readonly = any(kw in base_classes for kw in [
            'ReadOnly', 'ListAPIView', 'RetrieveAPIView',
        ])
        if is_readonly:
            continue

        # FinancialMutationViewSet inheritance implies compliance by design
        if 'FinancialMutationViewSet' in base_classes:
            continue

        # --- CRIT-02 FIX: Extract THIS class body only ---
        class_body = extract_class_body(content, match.start())

        if '@idempotent' in class_body:
            # Compliant — tag confirmed inside this class block
            continue

        # No @idempotent and not inheriting from FinancialMutationViewSet
        print(
            f"{RED}[FAIL] Idempotency Violation: class {class_name} "
            f"in {os.path.basename(filepath)}{RESET}"
        )
        print(f"       Inherits: {base_classes}")
        print(
            "       REQUIRED: Add '@idempotent' to class docstring "
            "OR inherit 'FinancialMutationViewSet'."
        )
        errors += 1

    return errors


def main() -> int:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    total_errors = 0
    files_checked = 0

    output_path = os.path.join(os.path.dirname(__file__), 'release_gate_idempotency_check.txt')
    with open(output_path, 'w', encoding='utf-8') as report:
        report.write("[AGRI-GUARDIAN] Idempotency Compliance Scan (v2 — Class-Level)\n")
        report.write("=" * 60 + "\n\n")

        for relative_dir in TARGET_APPS:
            abs_dir = os.path.join(root_dir, relative_dir)
            if not os.path.exists(abs_dir):
                report.write(f"[SKIP] Missing directory: {abs_dir}\n")
                continue

            for root, dirs, files in os.walk(abs_dir):
                # Skip test and migration directories
                dirs[:] = [d for d in dirs if d not in ('tests', 'migrations', '__pycache__')]
                for file in files:
                    if file.endswith(('.py',)) and 'test' not in file:
                        if file.endswith(('views.py', 'api.py', 'viewsets.py')):
                            fp = os.path.join(root, file)
                            report.write(f"Checking: {file}\n")
                            file_errors = check_file(fp)
                            total_errors += file_errors
                            files_checked += 1

        report.write(f"\nFiles checked: {files_checked}\n")
        if total_errors > 0:
            report.write(
                f"\nFAILED: {total_errors} idempotency violation(s) detected. "
                "RELEASE BLOCKED per AGENTS.md §Axis-2.\n"
            )
        else:
            report.write(
                "\nPASSED: All audited ViewSets are idempotency-compliant.\n"
            )
        print(f"{GREEN if total_errors == 0 else RED}"
              f"Idempotency check: {'PASSED' if total_errors == 0 else f'FAILED ({total_errors} errors)'}"
              f"{RESET}")

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
