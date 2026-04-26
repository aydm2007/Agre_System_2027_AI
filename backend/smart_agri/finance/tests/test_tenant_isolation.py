"""
[AGRI-GUARDIAN] Test Suite: Tenant Isolation for Financial Data
Target: FinancialLedgerViewSet, ActualExpenseViewSet
Protocol: "Data leakage between Farms is strictly prohibited" (Frontend Protocol II)
"""
import pytest
from decimal import Decimal
from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from smart_agri.finance.models import FinancialLedger, ActualExpense
from smart_agri.core.models.farm import Farm
from smart_agri.accounts.models import FarmMembership


@pytest.mark.django_db
class TestTenantIsolation(TestCase):
    """
    التحقق من عزل البيانات المالية بين المزارع.
    بروتوكول Agri-Guardian: تسرب البيانات بين المزارع ممنوع صراحةً.
    """

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="farmer_a", password="pass1234"
        )
        self.user_b = User.objects.create_user(
            username="farmer_b", password="pass1234"
        )
        self.superuser = User.objects.create_superuser(
            username="super_admin",
            email="super@example.com",
            password="pass1234",
        )

        # Farm model: name, slug, region (no owner_id)
        self.farm_a = Farm.objects.create(
            name="مزرعة أ", slug="farm-a", region="منطقة أ"
        )
        self.farm_b = Farm.objects.create(
            name="مزرعة ب", slug="farm-b", region="منطقة ب"
        )

        # Grant farm access via FarmMembership
        FarmMembership.objects.create(user=self.user_a, farm=self.farm_a, role="manager")
        FarmMembership.objects.create(user=self.user_b, farm=self.farm_b, role="manager")

        # Create ledger entries for each farm
        self.ledger_a = FinancialLedger.objects.create(
            farm=self.farm_a,
            account_code=FinancialLedger.ACCOUNT_LABOR,
            debit=Decimal("1000.0000"),
            credit=Decimal("0.0000"),
            description="Farm A labor cost",
            created_by=self.user_a,
        )
        self.ledger_b = FinancialLedger.objects.create(
            farm=self.farm_b,
            account_code=FinancialLedger.ACCOUNT_MATERIAL,
            debit=Decimal("2000.0000"),
            credit=Decimal("0.0000"),
            description="Farm B material cost",
            created_by=self.user_b,
        )

        # ActualExpense has no created_by field — just farm, amount, description, account_code
        self.expense_a = ActualExpense.objects.create(
            farm=self.farm_a,
            amount=Decimal("500.0000"),
            description="Farm A expense",
            account_code=FinancialLedger.ACCOUNT_OVERHEAD,
        )
        self.expense_b = ActualExpense.objects.create(
            farm=self.farm_b,
            amount=Decimal("750.0000"),
            description="Farm B expense",
            account_code=FinancialLedger.ACCOUNT_OVERHEAD,
        )

        self.client = APIClient()
        self.version = getattr(settings, "APP_VERSION", "2.0.0")

    def test_user_a_sees_only_farm_a_ledger(self):
        """
        اختبار: مستخدم المزرعة أ لا يرى سجلات دفتر الأستاذ الخاصة بالمزرعة ب.
        """
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            "/api/v1/finance/ledger/",
            HTTP_X_APP_VERSION=self.version,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        descriptions = [r["description"] for r in results]

        self.assertIn("Farm A labor cost", descriptions)
        self.assertNotIn("Farm B material cost", descriptions)

    def test_user_b_sees_only_farm_b_expenses(self):
        """
        اختبار: مستخدم المزرعة ب لا يرى مصروفات المزرعة أ.
        """
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get(
            "/api/v1/finance/expenses/",
            HTTP_X_APP_VERSION=self.version,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        descriptions = [r["description"] for r in results]

        self.assertIn("Farm B expense", descriptions)
        self.assertNotIn("Farm A expense", descriptions)

    def test_superuser_sees_all_data(self):
        """
        اختبار: المسؤول الأعلى (superuser) يرى جميع البيانات من كل المزارع.
        """
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            "/api/v1/finance/ledger/",
            HTTP_X_APP_VERSION=self.version,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        descriptions = [r["description"] for r in results]

        self.assertIn("Farm A labor cost", descriptions)
        self.assertIn("Farm B material cost", descriptions)
