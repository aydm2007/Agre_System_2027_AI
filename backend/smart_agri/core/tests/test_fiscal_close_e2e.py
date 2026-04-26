"""
[AGRI-GUARDIAN] Axis 3 Compliance: Fiscal Close E2E Integration Test
Tests the complete fiscal lifecycle: open → soft_close → hard_close
and verifies that ledger entries are rejected in closed periods.
"""
from decimal import Decimal
from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from smart_agri.core.models import Farm
from smart_agri.finance.models import (
    FiscalYear, FiscalPeriod, FinancialLedger,
)


class FiscalCloseE2ETests(TestCase):
    """Integration test: Full fiscal lifecycle without mocking."""

    def setUp(self):
        self.user = User.objects.create_user(username="fiscal_test_user")
        self.farm = Farm.objects.create(
            name="Fiscal Test Farm",
            slug="fiscal-test-farm",
            region="Sanaa",
            area=Decimal("50.00"),
        )
        self.fy = FiscalYear.objects.create(
            farm=self.farm,
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        # March period — matches today's date
        self.period = FiscalPeriod.objects.create(
            fiscal_year=self.fy,
            month=3,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            status=FiscalPeriod.STATUS_OPEN,
        )

    def _create_ledger_entry(self, desc="Test Entry"):
        """Helper: create a debit ledger entry."""
        return FinancialLedger.objects.create(
            farm=self.farm,
            account_code=FinancialLedger.ACCOUNT_LABOR,
            debit=Decimal("1000.0000"),
            credit=Decimal("0"),
            description=desc,
            created_by=self.user,
        )

    def test_open_period_accepts_entries(self):
        """Ledger entries allowed in open period."""
        entry = self._create_ledger_entry("Open period entry")
        self.assertIsNotNone(entry.pk)
        self.assertTrue(entry.is_posted)

    def test_soft_close_blocks_entries(self):
        """After soft_close, new entries are rejected."""
        self.period.status = FiscalPeriod.STATUS_SOFT_CLOSE
        self.period.save()

        with self.assertRaises(ValidationError):
            self._create_ledger_entry("Should be rejected - soft close")

    def test_hard_close_blocks_entries(self):
        """After hard_close, new entries are rejected."""
        self.period.status = FiscalPeriod.STATUS_SOFT_CLOSE
        self.period.save()
        self.period.status = FiscalPeriod.STATUS_HARD_CLOSE
        self.period.save()

        with self.assertRaises(ValidationError):
            self._create_ledger_entry("Should be rejected - hard close")

    def test_fiscal_state_machine_no_skip(self):
        """Cannot skip from open → hard_close directly."""
        self.period.status = FiscalPeriod.STATUS_HARD_CLOSE
        with self.assertRaises(ValidationError):
            self.period.full_clean()

    def test_fiscal_state_machine_no_reopen(self):
        """Cannot reopen a soft_closed period."""
        self.period.status = FiscalPeriod.STATUS_SOFT_CLOSE
        self.period.save()
        self.period.status = FiscalPeriod.STATUS_OPEN
        with self.assertRaises(ValidationError):
            self.period.full_clean()

    def test_hard_close_is_permanent(self):
        """Cannot reopen a hard_closed period."""
        self.period.status = FiscalPeriod.STATUS_SOFT_CLOSE
        self.period.save()
        self.period.status = FiscalPeriod.STATUS_HARD_CLOSE
        self.period.save()
        self.period.status = FiscalPeriod.STATUS_OPEN
        with self.assertRaises(ValidationError):
            self.period.full_clean()

    def test_ledger_immutability_no_update(self):
        """Existing ledger entries cannot be updated."""
        entry = self._create_ledger_entry("Immutable entry")
        entry.description = "Trying to change"
        with self.assertRaises(ValidationError):
            entry.save()

    def test_ledger_immutability_no_delete(self):
        """Existing ledger entries cannot be deleted."""
        entry = self._create_ledger_entry("Cannot delete")
        with self.assertRaises(ValidationError):
            entry.delete()

    def test_small_farm_cannot_hard_close_locally(self):
        """
        SMALL farm cannot hard-close locally without sector review.
        (Stub test)
        """
        pass

    def test_fiscal_year_auto_rollover(self):
        """
        Fiscal year auto-rollover after all periods closed.
        (Stub test)
        """
        pass
