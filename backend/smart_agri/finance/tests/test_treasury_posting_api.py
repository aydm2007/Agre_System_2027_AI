import calendar
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm
from smart_agri.finance.models import FinancialLedger, FiscalYear, FiscalPeriod
from smart_agri.finance.models_treasury import CashBox


class TestTreasuryPostingAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="treasury_admin",
            email="treasury@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=self.user)
        self.version = getattr(settings, "APP_VERSION", "2.0.0")

        self.farm = Farm.objects.create(name="Farm A")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Admin")

        # RLS bypass for setup writes (Postgres only).
        if connection.vendor == "postgresql":
            with connection.cursor() as c:
                c.execute("select set_config('app.user_id','-1',false)")

        self.cashbox = CashBox.objects.create(
            farm=self.farm,
            name="Main Safe",
            box_type=CashBox.MASTER_SAFE,
            currency="YER",
            balance=Decimal("1000.0000"),
        )

        today = timezone.localdate()
        fy = FiscalYear.objects.create(
            farm=self.farm,
            year=today.year,
            start_date=today.replace(month=1, day=1),
            end_date=today.replace(month=12, day=31),
            is_closed=False,
        )
        FiscalPeriod.objects.create(
            fiscal_year=fy,
            month=today.month,
            start_date=today.replace(day=1),
            end_date=today.replace(day=calendar.monthrange(today.year, today.month)[1]),
            status=FiscalPeriod.STATUS_OPEN,
            is_closed=False,
        )

    def test_create_treasury_transaction_posts_double_entry(self):
        payload = {
            "cash_box": self.cashbox.id,
            "transaction_type": "EXPENSE",
            "amount": "100.0000",
            "exchange_rate": "1.0000",
            "reference": "EXP-001",
            "note": "Fuel",
        }

        resp = self.client.post(
            "/api/v1/finance/treasury-transactions/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="treasury-exp-001",
            HTTP_X_FARM_ID=str(self.farm.id),
            HTTP_X_APP_VERSION=self.version,
        )
        self.assertIn(resp.status_code, [200, 201])
        tx_id = resp.json().get("id") if isinstance(resp.json(), dict) else None
        self.assertTrue(tx_id)

        # Ledger postings should exist
        qs = FinancialLedger.objects.filter(object_id=str(tx_id))
        self.assertEqual(qs.count(), 2)

        debit = qs.filter(debit__gt=0).first()
        credit = qs.filter(credit__gt=0).first()
        self.assertIsNotNone(debit)
        self.assertIsNotNone(credit)

        self.assertEqual(debit.debit, Decimal("100.0000"))
        self.assertEqual(credit.credit, Decimal("100.0000"))

        # Cashbox balance should decrease
        self.cashbox.refresh_from_db()
        self.assertEqual(self.cashbox.balance, Decimal("900.0000"))

    def test_update_endpoint_not_exposed(self):
        payload = {
            "cash_box": self.cashbox.id,
            "transaction_type": "RECEIPT",
            "amount": "50.0000",
        }

        resp = self.client.post(
            "/api/v1/finance/treasury-transactions/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="treasury-rcpt-001",
            HTTP_X_FARM_ID=str(self.farm.id),
            HTTP_X_APP_VERSION=self.version,
        )
        self.assertIn(resp.status_code, [200, 201])
        tx_id = resp.json().get("id")

        # ViewSet does not implement update.
        resp2 = self.client.put(
            f"/api/v1/finance/treasury-transactions/{tx_id}/",
            {"note": "mutate"},
            format="json",
            HTTP_X_APP_VERSION=self.version,
        )
        self.assertGreaterEqual(resp2.status_code, 400)
        self.assertLess(resp2.status_code, 500)
