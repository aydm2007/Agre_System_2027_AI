"""Read-only DailyLog remediation guard.

This helper is intentionally diagnostic-only. It verifies that the old one-step
DailyLog activity submission block is no longer present without mutating
frontend source files during release verification.
"""

from pathlib import Path


TARGET = Path("frontend/src/pages/DailyLog.jsx")
LEGACY_MARKER = "Create DailyLog first, then Activity"


def main() -> int:
    content = TARGET.read_text(encoding="utf-8")
    if LEGACY_MARKER in content:
        print(f"FAIL: legacy DailyLog submit marker remains in {TARGET}")
        return 1
    print(f"OK: {TARGET} no longer contains the legacy DailyLog submit marker.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
