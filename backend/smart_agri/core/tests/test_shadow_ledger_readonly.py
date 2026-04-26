from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import FinancialLedger


class ShadowLedgerReadOnlyTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username='shadow-ledger-admin',
            password='pass1234',
            email='shadow-ledger@example.com',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.farm = Farm.objects.create(name='Shadow Farm', slug='shadow-farm', region='R1')
        FarmSettings.objects.update_or_create(
            farm=self.farm,
            defaults={'mode': FarmSettings.MODE_SIMPLE},
        )
        FinancialLedger.objects.create(
            farm=self.farm,
            account_code=FinancialLedger.ACCOUNT_MATERIAL,
            debit=Decimal('150.0000'),
            credit=Decimal('0.0000'),
            description='Shadow daily entry',
            created_by=self.user,
            created_at=timezone.now() - timedelta(days=1),
        )
        FinancialLedger.objects.create(
            farm=self.farm,
            account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
            debit=Decimal('0.0000'),
            credit=Decimal('50.0000'),
            description='Shadow settlement entry',
            created_by=self.user,
            created_at=timezone.now() - timedelta(days=2),
        )

    def test_shadow_ledger_allows_read_only_daily_entries_in_simple(self):
        response = self.client.get('/api/v1/shadow-ledger/', {'farm': self.farm.id})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        rows = payload['results'] if isinstance(payload, dict) and 'results' in payload else payload
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['description'], 'Shadow settlement entry')
        self.assertEqual(rows[0]['credit'], '50.0000')
        self.assertEqual(rows[1]['description'], 'Shadow daily entry')
        self.assertEqual(rows[1]['debit'], '150.0000')

    def test_shadow_ledger_summary_returns_totals_for_same_filter_scope(self):
        response = self.client.get('/api/v1/shadow-ledger/summary/', {'farm': self.farm.id})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['totals']['entry_count'], 2)
        self.assertEqual(payload['totals']['debit'], 150.0)
        self.assertEqual(payload['totals']['credit'], 50.0)
        self.assertEqual(payload['totals']['balance'], 100.0)
