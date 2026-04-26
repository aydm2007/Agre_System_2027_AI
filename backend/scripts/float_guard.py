#!/usr/bin/env python
"""
Float Guard — Financial Integrity Linter
==========================================
[AGRI-GUARDIAN Axis 2 / AGENTS.md Rule#2]

Scans finance and core services for prohibited use of float() in
monetary / financial context. All monetary values MUST use Decimal.

Usage:
    python scripts/float_guard.py                  # scan and report
    python scripts/float_guard.py --strict         # exit code 1 on violations

Can be integrated as a pre-commit hook or CI step.
"""
import argparse
import ast
import sys
from pathlib import Path

# Directories to scan for float violations
SCAN_DIRS = [
    "smart_agri/finance/",
    "smart_agri/core/services/",
    "smart_agri/core/middleware/",
    "smart_agri/inventory/services/",
]

# Files or patterns to exclude from scanning
EXCLUDE_PATTERNS = [
    "__pycache__",
    "migrations/",
    "tests/",
    "test_",
]

# Allowlisted float usages (e.g., in non-monetary contexts)
ALLOWED_FLOAT_CONTEXTS = {
    "progress",
    "percentage",
    "ratio",
    "pct",
    "rate",
    "latitude",
    "longitude",
    "hectares",
}


class FloatViolationVisitor(ast.NodeVisitor):
    """AST visitor that detects float() calls in financial code."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: list[dict] = []

    def visit_Call(self, node: ast.Call):
        # Detect `float(...)` calls
        if isinstance(node.func, ast.Name) and node.func.id == "float":
            # Check if context suggests this is non-monetary
            line_context = ""
            if hasattr(node, "lineno"):
                line_context = f"line {node.lineno}"

            self.violations.append({
                "file": self.filename,
                "line": getattr(node, "lineno", 0),
                "col": getattr(node, "col_offset", 0),
                "type": "float_call",
                "message": f"float() used at {line_context}. Use Decimal() for monetary values.",
            })

        # Detect float literals in assignments (e.g., amount = 0.0)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Check for monetary-looking variable names assigned float literals
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, float):
            for target in node.targets:
                name = ""
                if isinstance(target, ast.Name):
                    name = target.id
                elif isinstance(target, ast.Attribute):
                    name = target.attr

                name_lower = name.lower()
                # Skip non-monetary float assignments
                if any(ctx in name_lower for ctx in ALLOWED_FLOAT_CONTEXTS):
                    continue

                monetary_keywords = {"amount", "price", "cost", "balance", "total",
                                    "debit", "credit", "tax", "fee", "salary", "wage",
                                    "payment", "receipt", "settlement", "fund", "budget"}
                if any(kw in name_lower for kw in monetary_keywords):
                    self.violations.append({
                        "file": self.filename,
                        "line": getattr(node, "lineno", 0),
                        "col": getattr(node, "col_offset", 0),
                        "type": "float_literal_monetary",
                        "message": f"Float literal assigned to monetary variable '{name}'. Use Decimal.",
                    })

        self.generic_visit(node)


def scan_file(filepath: Path) -> list[dict]:
    """Scan a single Python file for float violations."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    visitor = FloatViolationVisitor(str(filepath))
    visitor.visit(tree)
    return visitor.violations


def scan_directory(base_dir: Path, scan_dirs: list[str]) -> list[dict]:
    """Scan all Python files in specified directories."""
    all_violations = []
    for scan_dir in scan_dirs:
        target = base_dir / scan_dir
        if not target.exists():
            continue
        for py_file in target.rglob("*.py"):
            rel = str(py_file.relative_to(base_dir))
            if any(excl in rel for excl in EXCLUDE_PATTERNS):
                continue
            all_violations.extend(scan_file(py_file))
    return all_violations


def main():
    parser = argparse.ArgumentParser(
        description="Float Guard: scans financial code for prohibited float() usage."
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with code 1 if violations are found."
    )
    parser.add_argument(
        "--base-dir", type=str, default=".",
        help="Base directory of the backend code."
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    violations = scan_directory(base_dir, SCAN_DIRS)

    if not violations:
        print("✅ Float Guard: لا توجد انتهاكات. جميع القيم المالية تستخدم Decimal.")
        sys.exit(0)

    print(f"⚠️ Float Guard: تم العثور على {len(violations)} انتهاك(ات):")
    print("-" * 80)
    for v in violations:
        print(f"  {v['file']}:{v['line']}:{v['col']} — {v['message']}")
    print("-" * 80)
    print(
        "💡 استخدم Decimal('0.0000') بدلاً من float(). "
        "القيم المالية يجب أن تكون دقيقة (Exact Arithmetic)."
    )

    if args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
