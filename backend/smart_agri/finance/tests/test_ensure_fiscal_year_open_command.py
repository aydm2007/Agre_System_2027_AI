from datetime import date
from io import StringIO
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from smart_agri.core.models import AuditLog
from smart_agri.core.models.farm import Farm
from smart_agri.finance.models import FiscalPeriod, FiscalYear


class EnsureFiscalYearOpenCommandTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(
            name="Sardud Command Farm",
            slug=f"sardud-command-{uuid4().hex[:6]}",
        )

    def test_backfills_missing_periods_for_existing_year(self):
        fiscal_year = FiscalYear.objects.create(
            farm=self.farm,
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_closed=False,
        )
        FiscalPeriod.objects.create(
            fiscal_year=fiscal_year,
            month=4,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            status=FiscalPeriod.STATUS_OPEN,
            is_closed=False,
        )

        stdout = StringIO()
        call_command(
            "ensure_fiscal_year_open",
            "--farm",
            self.farm.slug,
            "--year",
            "2026",
            stdout=stdout,
        )

        fiscal_year.refresh_from_db()
        self.assertFalse(fiscal_year.is_closed)
        self.assertEqual(fiscal_year.periods.count(), 12)
        self.assertTrue(
            fiscal_year.periods.filter(month=5, status=FiscalPeriod.STATUS_OPEN).exists()
        )
        self.assertIn("created_periods=11", stdout.getvalue())

    def test_reopens_closed_year_and_periods_with_actor(self):
        user_model = get_user_model()
        actor = user_model.objects.create_superuser(
            username=f"fy-maint-{uuid4().hex[:8]}",
            email="fy-maint@example.com",
            password="pass1234",
        )
        fiscal_year = FiscalYear.objects.create(
            farm=self.farm,
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_closed=True,
        )
        FiscalPeriod.objects.create(
            fiscal_year=fiscal_year,
            month=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            status=FiscalPeriod.STATUS_HARD_CLOSE,
            is_closed=True,
            closed_by=actor,
        )

        call_command(
            "ensure_fiscal_year_open",
            "--farm",
            self.farm.slug,
            "--year",
            "2026",
            "--reopen-closed",
            "--actor-username",
            actor.username,
            "--reason",
            "Reopen 2026 for operations",
        )

        fiscal_year.refresh_from_db()
        period = fiscal_year.periods.get(month=1)
        self.assertFalse(fiscal_year.is_closed)
        self.assertEqual(period.status, FiscalPeriod.STATUS_OPEN)
        self.assertTrue(
            AuditLog.objects.filter(
                action="FISCAL_YEAR_REOPEN",
                object_id=str(fiscal_year.id),
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="FISCAL_PERIOD_REOPEN",
                object_id=str(period.id),
            ).exists()
        )
