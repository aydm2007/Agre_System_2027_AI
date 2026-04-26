from datetime import date
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.core.models import Farm, IdempotencyRecord
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import FiscalYear


class FiscalYearRolloverIdempotencyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="fiscal_admin",
            email="fiscal@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=self.admin)

        self.farm = Farm.objects.create(
            name="FY Rollover Farm",
            slug="fy-rollover-farm",
            region="north",
        )
        FarmSettings.objects.create(farm=self.farm, mode=FarmSettings.MODE_STRICT)
        self.client.credentials(HTTP_X_FARM_ID=str(self.farm.id))
        self.fiscal_year = FiscalYear.objects.create(
            farm=self.farm,
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_closed=True,
        )

    def _rollover_url(self):
        return f"/api/v1/finance/fiscal-years/{self.fiscal_year.id}/rollover/?farm={self.farm.id}"

    def _rollover_path(self):
        return f"/api/v1/finance/fiscal-years/{self.fiscal_year.id}/rollover/"

    def test_rollover_rejects_missing_idempotency_key(self):
        version = getattr(settings, "APP_VERSION", "2.0.0")
        response = self.client.post(
            self._rollover_url(),
            {"start_date": "2027-01-01", "end_date": "2027-12-31"},
            format="json",
            HTTP_X_APP_VERSION=version,
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json() if hasattr(response, "json") else {}
        self.assertIn("X-Idempotency-Key", str(payload))

    def test_rollover_replays_cached_response_for_duplicate_key(self):
        idem_key = "fy-rollover-dup-001"
        cached_payload = {"id": 909, "year": 2027, "cached": True}
        IdempotencyRecord.objects.create(
            key=idem_key,
            user=self.admin,
            method="POST",
            path=self._rollover_path(),
            model="FiscalYearViewSet",
            object_id="909",
            response_status=201,
            response_body=cached_payload,
        )

        with patch(
            "smart_agri.finance.services.fiscal_rollover_service.FiscalYearRolloverService.rollover_year"
        ) as mocked_rollover:
            response = self.client.post(
                self._rollover_url(),
                {"start_date": "2027-01-01", "end_date": "2027-12-31"},
                format="json",
                HTTP_X_IDEMPOTENCY_KEY=idem_key,
                HTTP_X_APP_VERSION=getattr(settings, "APP_VERSION", "2.0.0"),
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), cached_payload)
        mocked_rollover.assert_not_called()
