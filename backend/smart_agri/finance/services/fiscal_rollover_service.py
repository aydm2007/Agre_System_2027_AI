from calendar import monthrange
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from smart_agri.finance.models import FiscalYear, FiscalPeriod, FinancialLedger


class FiscalYearRolloverService:
    """
    Automates creation of the next fiscal year, month periods, and the opening journal.
    """

    @staticmethod
    def _normalize_dates(fy, start_date, end_date):
        next_start = start_date or fy.end_date + timedelta(days=1)
        next_end = end_date or (next_start.replace(year=next_start.year + 1) - timedelta(days=1))
        if next_end <= next_start:
            raise ValidationError("Next fiscal year end date must be after start date.")
        return next_start, next_end

    @staticmethod
    def _create_periods(fiscal_year):
        period_start = fiscal_year.start_date
        while period_start <= fiscal_year.end_date:
            year = period_start.year
            month = period_start.month
            # Determine last day of month
            _, last_day = monthrange(year, month)
            period_end = period_start.replace(day=last_day)
            if period_end > fiscal_year.end_date:
                period_end = fiscal_year.end_date

            FiscalPeriod.objects.create(
                fiscal_year=fiscal_year,
                month=month,
                start_date=period_start,
                end_date=period_end,
                status=FiscalPeriod.STATUS_OPEN,
                is_closed=False,
            )

            # move to first day of next month
            next_month = period_start + timedelta(days=last_day)
            period_start = next_month

    @staticmethod
    def _create_opening_entries(fy, next_year, user):
        balances = (
            FinancialLedger.objects.filter(
                farm=fy.farm,
                created_at__date__gte=fy.start_date,
                created_at__date__lte=fy.end_date,
            )
            .values("account_code")
            .annotate(debits=Sum("debit"), credits=Sum("credit"))
        )

        defaults = {
            "description": f"Opening balance rollover for Fiscal Year {next_year.year}",
            "currency": getattr(settings, "DEFAULT_CURRENCY", "YER"),
            "farm": fy.farm,
            "activity": None,
            "created_by": user,
        }

        entries = []
        for account in balances:
            net = (Decimal(account["debits"] or 0) - Decimal(account["credits"] or 0)).quantize(
                Decimal("0.0001")
            )
            if net == 0:
                continue
            debit = net if net > 0 else Decimal("0")
            credit = abs(net) if net < 0 else Decimal("0")
            entries.append(
                FinancialLedger(
                    account_code=account["account_code"],
                    debit=debit,
                    credit=credit,
                    **defaults,
                )
            )

        if entries:
            # [AGRI-GUARDIAN] Individual save() ensures clean() runs fiscal period
            # checks and row_hash computation for each opening balance entry.
            for entry in entries:
                entry.created_by = user
                entry.save()

    @staticmethod
    @transaction.atomic
    def rollover_year(fiscal_year_id: int, new_start_date=None, new_end_date=None, user=None):
        fy = FiscalYear.objects.select_for_update().get(pk=fiscal_year_id)
        if not fy.is_closed:
            raise ValidationError("Fiscal year must be hard closed before rollover.")

        active_periods = fy.periods.exclude(status=FiscalPeriod.STATUS_HARD_CLOSE)
        if active_periods.exists():
            raise ValidationError("All periods must be hard closed before rollover.")

        target_year = fy.year + 1
        if FiscalYear.objects.filter(farm=fy.farm, year=target_year, deleted_at__isnull=True).exists():
            raise ValidationError(f"Fiscal year {target_year} already exists.")

        start_date, end_date = FiscalYearRolloverService._normalize_dates(fy, new_start_date, new_end_date)

        next_year = FiscalYear.objects.create(
            farm=fy.farm,
            year=target_year,
            start_date=start_date,
            end_date=end_date,
            is_closed=False,
        )

        FiscalYearRolloverService._create_periods(next_year)
        FiscalYearRolloverService._create_opening_entries(fy, next_year, user)

        return next_year
