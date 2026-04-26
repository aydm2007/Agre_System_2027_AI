import calendar
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm
from smart_agri.finance.models import FinancialLedger, FiscalPeriod, FiscalYear
from smart_agri.integrations.models import ExternalFinanceBatch


class ExternalFinanceBatchApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="sector_admin",
            email="sector@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name="Aljurobah")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Admin")

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

        self.batch = ExternalFinanceBatch.objects.create(
            farm=self.farm,
            period_start=today.replace(day=1),
            period_end=today,
        )

    def _create_unbalanced_ledger(self):
        FinancialLedger.objects.create(
            farm=self.farm,
            account_code=FinancialLedger.ACCOUNT_OVERHEAD,
            debit=Decimal("100.0000"),
            credit=Decimal("0.0000"),
            description="Unbalanced debit row 1",
            currency="YER",
            created_by=self.user,
        )
        FinancialLedger.objects.create(
            farm=self.farm,
            account_code=FinancialLedger.ACCOUNT_OVERHEAD,
            debit=Decimal("50.0000"),
            credit=Decimal("0.0000"),
            description="Unbalanced debit row 2",
            currency="YER",
            created_by=self.user,
        )

    def test_build_from_ledger_blocks_unbalanced_batch_and_replays(self):
        self._create_unbalanced_ledger()
        headers = {"HTTP_X_IDEMPOTENCY_KEY": "ext-batch-build-001"}
        url = f"/api/v1/integrations/finance-batches/{self.batch.id}/build-from-ledger/"

        first = self.client.post(url, {}, format="json", **headers)
        self.assertEqual(first.status_code, 400)
        self.assertIn("unbalanced", first.json().get("detail", "").lower())

        second = self.client.post(url, {}, format="json", **headers)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.json(), first.json())

        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, ExternalFinanceBatch.STATUS_FAILED)

    def test_acknowledge_requires_key_and_replays(self):
        self.batch.status = ExternalFinanceBatch.STATUS_EXPORTED
        self.batch.save(update_fields=["status", "updated_at"])
        url = f"/api/v1/integrations/finance-batches/{self.batch.id}/acknowledge/"

        missing_key = self.client.post(url, {"external_ref": "ACK-1"}, format="json")
        self.assertEqual(missing_key.status_code, 400)

        headers = {"HTTP_X_IDEMPOTENCY_KEY": "ext-batch-ack-001"}
        first = self.client.post(url, {"external_ref": "ACK-1"}, format="json", **headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json().get("status"), "acknowledged")

        second = self.client.post(url, {"external_ref": "ACK-1"}, format="json", **headers)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json(), first.json())

