from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = REPO_ROOT / "docs" / "reports"
DRILL_PATTERN = re.compile(r"^DR_DRILL_(\d{4}-\d{2}-\d{2})\.md$")
MAX_AGE_DAYS = 31


def parse_date_from_filename(path: Path) -> date | None:
    match = DRILL_PATTERN.match(path.name)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y-%m-%d").date()


def main() -> int:
    if not REPORTS_DIR.exists():
        print("BLOCK: docs/reports directory is missing.")
        return 1

    candidates = []
    for path in REPORTS_DIR.glob("DR_DRILL_*.md"):
        report_date = parse_date_from_filename(path)
        if report_date is not None:
            candidates.append((report_date, path))

    if not candidates:
        print("BLOCK: No DR drill evidence file found (expected docs/reports/DR_DRILL_<YYYY-MM-DD>.md).")
        return 1

    latest_date, latest_path = sorted(candidates, key=lambda item: item[0])[-1]
    age_days = (date.today() - latest_date).days

    if age_days > MAX_AGE_DAYS:
        print(
            f"BLOCK: Latest DR drill evidence is stale ({latest_path.name}, {age_days} days old, max {MAX_AGE_DAYS})."
        )
        return 1

    content = latest_path.read_text(encoding="utf-8", errors="replace")
    required_fields = [
        "DRILL_DATE",
        "SCENARIO",
        "RTO_TARGET_MINUTES",
        "RTO_ACTUAL_MINUTES",
        "RPO_TARGET_MINUTES",
        "RPO_ACTUAL_MINUTES",
        "RESULT",
        "EVIDENCE_COMMANDS",
    ]
    missing = [field for field in required_fields if field not in content]
    if missing:
        print(f"BLOCK: Latest DR drill evidence {latest_path.name} is missing required fields: {missing}")
        return 1

    print(f"PASS: DR drill evidence is fresh ({latest_path.name}, {age_days} days old).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
