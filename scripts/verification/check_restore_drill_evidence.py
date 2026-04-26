from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = REPO_ROOT / "docs" / "reports"
DRILL_PATTERN = re.compile(r"^DR_DRILL_(\d{4}-\d{2}-\d{2})\.md$")


def latest_drill_report() -> Path | None:
    candidates: list[tuple[datetime, Path]] = []
    for path in REPORTS_DIR.glob("DR_DRILL_*.md"):
        match = DRILL_PATTERN.match(path.name)
        if not match:
            continue
        report_date = datetime.strptime(match.group(1), "%Y-%m-%d")
        candidates.append((report_date, path))

    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0])[-1][1]


def main() -> int:
    report = latest_drill_report()
    if report is None:
        print("BLOCK: No DR drill report found for restore evidence validation.")
        return 1

    content = report.read_text(encoding="utf-8", errors="replace")
    required_tokens = [
        "RESULT: PASS",
        "restore",
        "showmigrations",
        "migrate --plan",
        "manage.py check",
    ]

    missing = [token for token in required_tokens if token.lower() not in content.lower()]
    if missing:
        print(f"BLOCK: DR drill report {report.name} lacks required restore evidence tokens: {missing}")
        return 1

    print(f"PASS: Restore drill evidence validated in {report.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
