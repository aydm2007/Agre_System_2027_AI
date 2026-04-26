from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "docs" / "reports"
TEMPLATE = REPORTS_DIR / "WEEKLY_AXIS_SCORECARD_TEMPLATE.md"


def main() -> int:
    if not TEMPLATE.exists():
        raise SystemExit(f"Template missing: {TEMPLATE}")

    today = date.today().isoformat()
    output = REPORTS_DIR / f"WEEKLY_AXIS_SCORECARD_{today}.md"
    if output.exists():
        print(f"Scorecard already exists: {output}")
        return 0

    content = TEMPLATE.read_text(encoding="utf-8")
    content = content.replace("<YYYY-MM-DD>", today)
    output.write_text(content, encoding="utf-8")
    print(f"Created scorecard: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
