from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")

import django  # noqa: E402

django.setup()

from smart_agri.finance.models import FinancialLedger, FiscalPeriod  # noqa: E402


def main() -> int:
    violations: list[str] = []

    unposted_count = FinancialLedger.objects.filter(is_posted=False).count()
    if unposted_count:
        violations.append(
            f"Found {unposted_count} unposted FinancialLedger rows (is_posted=false)."
        )

    legacy_count = FiscalPeriod.objects.filter(
        status__in=[
            FiscalPeriod.LEGACY_STATUS_SOFT_CLOSED,
            FiscalPeriod.LEGACY_STATUS_HARD_CLOSED,
        ]
    ).count()
    if legacy_count:
        violations.append(
            f"Found {legacy_count} fiscal periods using legacy status values (soft_closed/hard_closed)."
        )

    hard_closed_without_stamp = FiscalPeriod.objects.filter(
        status=FiscalPeriod.STATUS_HARD_CLOSE,
        closed_at__isnull=True,
    ).count()
    if hard_closed_without_stamp:
        violations.append(
            f"Found {hard_closed_without_stamp} hard-closed fiscal periods without closed_at timestamp."
        )

    suspicious_post_close_rows = 0
    for period in FiscalPeriod.objects.filter(
        status=FiscalPeriod.STATUS_HARD_CLOSE,
        closed_at__isnull=False,
    ).select_related("fiscal_year__farm"):
        rows = FinancialLedger.objects.filter(
            farm=period.fiscal_year.farm,
            created_at__gt=period.closed_at,
            created_at__date__gte=period.start_date,
            created_at__date__lte=period.end_date,
        ).count()
        suspicious_post_close_rows += rows

    if suspicious_post_close_rows:
        violations.append(
            f"Detected {suspicious_post_close_rows} ledger rows created after hard-close timestamp in closed periods."
        )

    if violations:
        print("BLOCK: Runtime financial integrity probe failed.")
        for item in violations:
            print(f"- {item}")
        return 1

    print("PASS: Runtime financial integrity probe passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
