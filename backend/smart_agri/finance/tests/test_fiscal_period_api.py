from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from smart_agri.core.models import FarmSettings
from smart_agri.core.models.farm import Farm
from smart_agri.finance.models import FiscalPeriod, FiscalYear


class FiscalPeriodApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username=f"fiscal-api-{uuid4().hex[:8]}",
            email="fiscal-api@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(self.user)

        today = timezone.localdate()
        self.farm_a = Farm.objects.create(name="Fiscal Farm A", slug=f"fiscal-a-{uuid4().hex[:6]}")
        self.farm_b = Farm.objects.create(name="Fiscal Farm B", slug=f"fiscal-b-{uuid4().hex[:6]}")
        FarmSettings.objects.create(farm=self.farm_a, mode=FarmSettings.MODE_STRICT)
        FarmSettings.objects.create(farm=self.farm_b, mode=FarmSettings.MODE_STRICT)

        self.year_a = FiscalYear.objects.create(
            farm=self.farm_a,
            year=2026,
            start_date=today,
            end_date=today + timedelta(days=365),
        )
        self.year_b = FiscalYear.objects.create(
            farm=self.farm_b,
            year=2026,
            start_date=today,
            end_date=today + timedelta(days=365),
        )
        self.period = FiscalPeriod.objects.create(
            fiscal_year=self.year_a,
            month=1,
            start_date=today,
            end_date=today + timedelta(days=30),
            status=FiscalPeriod.STATUS_HARD_CLOSE,
            is_closed=True,
            closed_at=timezone.now(),
            closed_by=self.user,
        )

    def test_fiscal_years_filter_by_farm_query_param(self):
        response = self.client.get('/api/v1/finance/fiscal-years/', {'farm': self.farm_a.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        returned_ids = {entry['id'] for entry in results}
        self.assertIn(self.year_a.id, returned_ids)
        self.assertNotIn(self.year_b.id, returned_ids)

    def test_reopen_endpoint_reopens_period_with_reason(self):
        response = self.client.post(
            f'/api/v1/finance/fiscal-periods/{self.period.id}/reopen/',
            {'reason': 'Need to fix final posting'},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='reopen-period-001',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, FiscalPeriod.STATUS_OPEN)
        self.assertEqual(response.data['period_status'], FiscalPeriod.STATUS_OPEN)
