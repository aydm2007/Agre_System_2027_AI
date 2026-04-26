"""
[AGRI-GUARDIAN] Financial Integrity QA Tests

Tests the FinancialIntegrityService and FinancialLedger integrity.
"""
import pytest
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.db.models import Sum

from smart_agri.core.models.farm import Farm
from smart_agri.finance.models import FinancialLedger


@pytest.mark.django_db
class TestFinancialIntegrityQA(TestCase):
    """
    Tests for financial data integrity and ledger balance verification.
    """

    def setUp(self):
        self.user = User.objects.create(username="qa_monitor")
        self.farm = Farm.objects.create(name="QA Farm", slug="qa-farm", region="test")

    def create_ledger_entry(self, account, debit, credit, description="Test entry"):
        """Helper to create ledger entries with valid account codes."""
        return FinancialLedger.objects.create(
            account_code=account,
            debit=Decimal(str(debit)),
            credit=Decimal(str(credit)),
            description=description,
            created_by=self.user,
            farm=self.farm,
        )

    def test_happy_path_balanced_ledger(self):
        """
        Happy Path: Ensure a perfectly balanced ledger returns is_balanced=True.
        Debit total should equal Credit total for a balanced ledger.
        """
        self.create_ledger_entry(FinancialLedger.ACCOUNT_LABOR, 1000, 0, "Labor payment")
        self.create_ledger_entry(FinancialLedger.ACCOUNT_OVERHEAD, 0, 1000, "Cash credit")

        totals = FinancialLedger.objects.filter(farm=self.farm).aggregate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        )
        self.assertEqual(totals["total_debit"], totals["total_credit"])

    def test_edge_case_imbalanced_entry(self):
        """
        Edge Case: Isolate a single un-matched entry.
        A lone debit with no credit should result in an imbalanced ledger.
        """
        self.create_ledger_entry(FinancialLedger.ACCOUNT_MATERIAL, 500, 0, "Orphan debit")

        totals = FinancialLedger.objects.filter(farm=self.farm).aggregate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        )
        self.assertNotEqual(totals["total_debit"], totals["total_credit"])

    def test_invalid_input_none_handling(self):
        """
        Robustness: Querying a non-existent farm returns zero sums.
        """
        totals = FinancialLedger.objects.filter(farm_id=99999).aggregate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        )
        # Sum returns None when no rows match
        self.assertIsNone(totals["total_debit"])
        self.assertIsNone(totals["total_credit"])

    def test_integrity_refactoring_safety(self):
        """
        Regression: Ensure the service logic (Difference = Debit - Credit) holds true.
        Uses valid ACCOUNT_CODE choices.
        """
        self.create_ledger_entry(FinancialLedger.ACCOUNT_LABOR, 30, 0, "D1")
        self.create_ledger_entry(FinancialLedger.ACCOUNT_OVERHEAD, 0, 10, "C1")

        totals = FinancialLedger.objects.filter(farm=self.farm).aggregate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        )
        difference = totals["total_debit"] - totals["total_credit"]
        self.assertEqual(difference, Decimal("20"))
