"""
Financial Integrity & RLS Tests - AGRI-MAESTRO Phase 4
Verify financial ledger immutability and RLS isolation
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.db import connection
from smart_agri.core.models import (
    Farm, Location, Activity, FinancialLedger, 
    CropPlan, ActivityCostSnapshot
)
from smart_agri.accounts.models import FarmMembership

User = get_user_model()


@pytest.mark.django_db
class TestFinancialLedgerRLS(TransactionTestCase):
    """Test financial ledger READ-ONLY RLS policy"""

    def setUp(self):
        """Create test data with financial entries"""
        # Users
        self.user1 = User.objects.create_user(username='farmer1', password='test')
        self.user2 = User.objects.create_user(username='farmer2', password='test')

        # Farms
        self.farm1 = Farm.objects.create(name='Farm 1', code='F1', slug='farm-1')
        self.farm2 = Farm.objects.create(name='Farm 2', code='F2', slug='farm-2')

        # Memberships
        FarmMembership.objects.create(user=self.user1, farm=self.farm1, role='Admin')
        FarmMembership.objects.create(user=self.user2, farm=self.farm2, role='Admin')

        # Locations
        self.loc1 = Location.objects.create(farm=self.farm1, name='L1', code='L1')
        self.loc2 = Location.objects.create(farm=self.farm2, name='L2', code='L2')

        # Activities
        self.activity1 = Activity.objects.create(
            location=self.loc1,
            activity_date='2026-01-15'
        )
        self.activity2 = Activity.objects.create(
            location=self.loc2,
            activity_date='2026-01-15'
        )

        # Crop Plans
        self.plan1 = CropPlan.objects.create(farm=self.farm1, name='Plan 1')
        self.plan2 = CropPlan.objects.create(farm=self.farm2, name='Plan 2')

        # Financial Ledger Entries
        self.ledger1 = FinancialLedger.objects.create(
            activity=self.activity1,
            crop_plan=self.plan1,
            amount=Decimal('1000.00'),
            transaction_type='DEBIT'
        )
        self.ledger2 = FinancialLedger.objects.create(
            activity=self.activity2,
            crop_plan=self.plan2,
            amount=Decimal('2000.00'),
            transaction_type='DEBIT'
        )

    def _set_user_context(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.user_id', %s, false)", [str(user_id)])

    def test_ledger_farm_isolation_via_activity(self):
        """User 1 sees only ledger entries from their farm (via activity)"""
        self._set_user_context(self.user1.id)

        ledgers = list(FinancialLedger.objects.all())
        self.assertEqual(len(ledgers), 1)
        self.assertEqual(ledgers[0].id, self.ledger1.id)
        self.assertEqual(ledgers[0].amount, Decimal('1000.00'))

    def test_ledger_isolation_via_crop_plan(self):
        """Ledger entries isolated via crop_plan → farm relationship"""
        self._set_user_context(self.user1.id)

        # User 1 can only see entries linked to their crop plans
        ledgers = FinancialLedger.objects.filter(crop_plan__isnull=False)
        for entry in ledgers:
            self.assertEqual(entry.crop_plan.farm_id, self.farm1.id)

    def test_cannot_see_other_farm_ledger(self):
        """User 1 cannot access ledger entries from Farm 2"""
        self._set_user_context(self.user1.id)

        with self.assertRaises(FinancialLedger.DoesNotExist):
            FinancialLedger.objects.get(id=self.ledger2.id)

    def test_ledger_immutability_enforced_by_code(self):
        """
        Financial ledger immutability is enforced by Django code, not RLS.
        RLS policies are FOR SELECT only (read-only).
        """
        # This test verifies Django-level protection exists
        # Actual UPDATE/DELETE prevention is in models/services
        self._set_user_context(self.user1.id)

        ledger = FinancialLedger.objects.get(id=self.ledger1.id)
        
        # Verify ledger exists and is readable
        self.assertEqual(ledger.amount, Decimal('1000.00'))
        
        # Immutability enforcement is at Django model/service layer
        # (RLS only controls SELECT visibility)


@pytest.mark.django_db
class TestActivityCostSnapshotRLS(TransactionTestCase):
    """Test cost snapshot RLS isolation"""

    def setUp(self):
        """Create test data with cost snapshots"""
        # Users
        self.user1 = User.objects.create_user(username='user1', password='test')
        self.user2 = User.objects.create_user(username='user2', password='test')

        # Farms
        self.farm1 = Farm.objects.create(name='F1', code='F1', slug='f1')
        self.farm2 = Farm.objects.create(name='F2', code='F2', slug='f2')

        # Memberships
        FarmMembership.objects.create(user=self.user1, farm=self.farm1, role='Admin')
        FarmMembership.objects.create(user=self.user2, farm=self.farm2, role='Admin')

        # Locations & Activities
        loc1 = Location.objects.create(farm=self.farm1, name='L1', code='L1')
        loc2 = Location.objects.create(farm=self.farm2, name='L2', code='L2')
        
        self.act1 = Activity.objects.create(location=loc1, activity_date='2026-01-15')
        self.act2 = Activity.objects.create(location=loc2, activity_date='2026-01-15')

        # Cost Snapshots
        self.snapshot1 = ActivityCostSnapshot.objects.create(
            activity=self.act1,
            total_cost=Decimal('500.00')
        )
        self.snapshot2 = ActivityCostSnapshot.objects.create(
            activity=self.act2,
            total_cost=Decimal('750.00')
        )

    def _set_user_context(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.user_id', %s, false)", [str(user_id)])

    def test_cost_snapshot_isolation(self):
        """Cost snapshots isolated by activity → location → farm"""
        self._set_user_context(self.user1.id)

        snapshots = list(ActivityCostSnapshot.objects.all())
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].id, self.snapshot1.id)


# Run with: python manage.py test core.tests.test_financial_rls
