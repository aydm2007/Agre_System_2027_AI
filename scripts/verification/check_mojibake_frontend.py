#!/usr/bin/env python3
"""
Fail CI when frontend source contains mojibake artifacts.

Scope: frontend/src/**/*.{js,jsx,ts,tsx}
"""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = ROOT / "frontend" / "src"
EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}

# Common mojibake markers observed in Arabic UTF-8 text rendered as CP1252/Latin-1.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("arabic_mojibake_primary", re.compile(r"(Ø.|Ù.)")),
    ("utf8_latin1_fragment", re.compile(r"(?:Ã.|Â.)")),
    ("replacement_char", re.compile(r"(?:ï¿½|�)")),
    ("emoji_mojibake", re.compile(r"(?:âœ|âš|ðŸ)")),
]


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    findings: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        findings.append((0, "decode_error", "file is not valid UTF-8"))
        return findings

    for lineno, line in enumerate(text.splitlines(), start=1):
        for label, pattern in PATTERNS:
            match = pattern.search(line)
            if match:
                snippet = line.strip()
                if len(snippet) > 180:
                    snippet = snippet[:177] + "..."
                findings.append((lineno, label, snippet))
                break
    return findings


def iter_source_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            yield path


def main() -> int:
    if not FRONTEND_SRC.exists():
        print(f"SKIP: {FRONTEND_SRC} not found")
        return 0

    all_findings: list[tuple[Path, int, str, str]] = []
    for source in iter_source_files(FRONTEND_SRC):
        findings = scan_file(source)
        for lineno, label, snippet in findings:
            all_findings.append((source, lineno, label, snippet))

    if all_findings:
        print("Mojibake detection failed:")
        for source, lineno, label, snippet in all_findings:
            rel = source.relative_to(ROOT)
            print(f" - {rel}:{lineno} [{label}] {snippet}")
        return 1

    print("OK: No mojibake markers detected in frontend/src.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

