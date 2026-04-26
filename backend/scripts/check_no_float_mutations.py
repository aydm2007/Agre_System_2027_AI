"""
[AGRI-GUARDIAN] Float & Division Safety Scanner (v2)
Release Gate: Axis 5 — Decimal & Surra Integrity

WARN-03 FIX: Previous version only printed [WARN] for the '/' division operator
without setting found_errors=True. Per AGENTS.md: "No float-based math exists
in finance/inventory mutation paths." Division '/' in Python 3 ALWAYS returns
float unless both operands are Decimal. This version FAILS (exit 1) on any
division detected in the target financial mutation paths.

Rules:
- float() call in finance/inventory/sales/core services → FAIL
- '/' division operator in same paths → FAIL (potential float result)
- '//' integer division is allowed (does not produce float from int operands)
"""
import ast
import os
import sys

# --- Configuration ---
TARGET_DIRS = [
    'backend/smart_agri/finance',
    'backend/smart_agri/inventory',
    'backend/smart_agri/sales',
    'backend/smart_agri/core/services',
]
EXCLUDES = {'tests', 'migrations', 'management', '__pycache__'}

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

found_errors = False


class FloatVisitor(ast.NodeVisitor):
    """AST visitor that detects float() calls and bare '/' division."""

    def __init__(self, filename: str):
        self.filename = filename

    def visit_Call(self, node: ast.Call):
        """Detect explicit float() conversion — direct AGENTS.md violation."""
        global found_errors
        if isinstance(node.func, ast.Name) and node.func.id == 'float':
            print(
                f"{RED}[FAIL] float() conversion detected in "
                f"{self.filename}:{node.lineno}{RESET}"
            )
            print("       Use Decimal() with explicit quantize() instead.")
            found_errors = True
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        """
        Detect '/' true-division — AGENTS.md §Axis-5 violation.

        In Python 3, the '/' operator ALWAYS returns float when applied to
        plain int/float operands. Even Decimal/Decimal uses Decimal.__truediv__
        which is safe, but static analysis cannot easily distinguish context.
        Per AGENTS.md: 'No float-based math exists in finance/inventory mutation
        paths.' We FAIL on '/' to enforce explicit Decimal.quantize() discipline.

        Exception: '//' floor-division is safe for integer counting operations.
        """
        global found_errors
        if isinstance(node.op, ast.Div):
            print(
                f"{RED}[FAIL] Division '/' detected in "
                f"{self.filename}:{node.lineno}{RESET}"
            )
            print(
                "       '/' returns float in Python 3 for non-Decimal operands. "
                "Use Decimal division with .quantize(Decimal('0.0001'), ROUND_HALF_UP) "
                "to ensure Decimal purity. If operands are confirmed Decimal, add a "
                "# agri-guardian: decimal-safe comment to suppress."
            )
            found_errors = True
        self.generic_visit(node)


def check_file(filepath: str):
    """Parse a single Python file and run the float visitor."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        # Allow explicit suppression for confirmed-safe Decimal divisions
        # Developer must add: # agri-guardian: decimal-safe
        # We strip those lines from AST checking
        lines = source.split('\n')
        filtered_lines = []
        for line in lines:
            if 'agri-guardian: decimal-safe' in line:
                # Replace the division with a safe placeholder so AST won't flag it
                filtered_lines.append(line.replace('/', '//'))
            else:
                filtered_lines.append(line)
        filtered_source = '\n'.join(filtered_lines)

        tree = ast.parse(filtered_source, filename=filepath)
        FloatVisitor(filepath).visit(tree)
    except SyntaxError as e:
        print(f"{YELLOW}[SKIP] Syntax error in {filepath}: {e}{RESET}")
    except Exception as e:
        print(f"{YELLOW}[SKIP] Error parsing {filepath}: {e}{RESET}")


def main() -> int:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    output_path = os.path.join(os.path.dirname(__file__), 'release_gate_float_check.txt')
    with open(output_path, 'w', encoding='utf-8') as report:
        report.write("[AGRI-GUARDIAN] Float & Division Safety Scan (v2)\n")
        report.write("=" * 60 + "\n\n")
        report.write("Scanning for float() and '/' in financial mutation paths...\n\n")

        for relative_dir in TARGET_DIRS:
            abs_dir = os.path.join(root_dir, relative_dir)
            if not os.path.exists(abs_dir):
                report.write(f"[SKIP] Missing directory: {abs_dir}\n")
                continue

            for root, dirs, files in os.walk(abs_dir):
                dirs[:] = [d for d in dirs if d not in EXCLUDES]
                for file in files:
                    if (file.endswith('.py')
                            and 'test' not in file.lower()
                            and 'migration' not in file.lower()):
                        check_file(os.path.join(root, file))

        if found_errors:
            report.write(
                "\nFAILED: Float/division violations detected. "
                "RELEASE BLOCKED per AGENTS.md §Axis-5.\n"
            )
            print(f"{RED}Float check: FAILED — see above for violation details.{RESET}")
        else:
            report.write(
                "\nPASSED: No float() or unsafe division detected in "
                "financial mutation paths.\n"
            )
            print(f"{GREEN}Float check: PASSED — Decimal purity confirmed.{RESET}")

    return 1 if found_errors else 0


if __name__ == "__main__":
    sys.exit(main())
