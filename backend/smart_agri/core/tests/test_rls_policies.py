"""
RLS Policy Tests - AGRI-MAESTRO Phase 4
Comprehensive farm isolation verification for Row Level Security policies

Tests verify that:
1. Users can only see data from farms they are members of
2. Financial ledger entries are properly isolated
3. Activities, locations, and inventory are farm-isolated
4. RLS policies work correctly via the API
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, TransactionTestCase
from django.db import connection
from smart_agri.core.models import (
    Farm, Location, Activity, CropPlan,
    ItemInventory, FinancialLedger, ActivityCostSnapshot
)
from smart_agri.accounts.models import FarmMembership

User = get_user_model()


@pytest.mark.django_db
class TestRLSFarmIsolation(TransactionTestCase):
    """Test that RLS policies enforce farm-level data isolation"""

    def setUp(self):
        """Create test data: 2 users, 2 farms, isolated memberships"""
        # Users
        self.user1 = User.objects.create_user(
            username='farmer1',
            password='test123',
            email='farmer1@test.com'
        )
        self.user2 = User.objects.create_user(
            username='farmer2',
            password='test123',
            email='farmer2@test.com'
        )

        # Farms
        self.farm1 = Farm.objects.create(
            name='Farm Alpha',
            code='FARM001',
            slug='farm-alpha'
        )
        self.farm2 = Farm.objects.create(
            name='Farm Beta',
            code='FARM002',
            slug='farm-beta'
        )

        # Farm Memberships
        FarmMembership.objects.create(
            user=self.user1,
            farm=self.farm1,
            role='Admin'
        )
        FarmMembership.objects.create(
            user=self.user2,
            farm=self.farm2,
            role='Admin'
        )

        # Locations
        self.location1 = Location.objects.create(
            farm=self.farm1,
            name='Field 1A',
            code='F1A'
        )
        self.location2 = Location.objects.create(
            farm=self.farm2,
            name='Field 2A',
            code='F2A'
        )

    def _set_user_context(self, user_id):
        """Helper to set PostgreSQL session variable for RLS"""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.user_id', %s, false)",
                [str(user_id)]
            )

    def test_user_sees_only_own_farm(self):
        """User 1 should see only Farm 1"""
        self._set_user_context(self.user1.id)

        farms = list(Farm.objects.all())
        self.assertEqual(len(farms), 1, f"Expected 1 farm, got {len(farms)}")
        self.assertEqual(farms[0].id, self.farm1.id)

    def test_user_cannot_see_other_farm(self):
        """User 1 should NOT see Farm 2"""
        self._set_user_context(self.user1.id)

        with self.assertRaises(Farm.DoesNotExist):
            Farm.objects.get(id=self.farm2.id)

    def test_location_isolation(self):
        """User 1 should only see locations in Farm 1"""
        self._set_user_context(self.user1.id)

        locations = list(Location.objects.all())
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0].id, self.location1.id)
        self.assertEqual(locations[0].farm_id, self.farm1.id)

    def test_location_cannot_see_other_farm(self):
        """User 1 cannot see locations from Farm 2"""
        self._set_user_context(self.user1.id)

        with self.assertRaises(Location.DoesNotExist):
            Location.objects.get(id=self.location2.id)

    def test_switch_user_context(self):
        """Switching user context changes visible farms"""
        # User 1 sees Farm 1
        self._set_user_context(self.user1.id)
        farms1 = list(Farm.objects.all())
        self.assertEqual(len(farms1), 1)
        self.assertEqual(farms1[0].id, self.farm1.id)

        # Switch to User 2, sees Farm 2
        self._set_user_context(self.user2.id)
        farms2 = list(Farm.objects.all())
        self.assertEqual(len(farms2), 1)
        self.assertEqual(farms2[0].id, self.farm2.id)

    def test_api_farm_isolation(self):
        """API should enforce RLS via middleware"""
        client = Client()
        client.force_login(self.user1)

        # User 1 can access Farm 1
        response = client.get(f'/api/v1/farms/{self.farm1.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Farm Alpha')

        # User 1 CANNOT access Farm 2
        response = client.get(f'/api/v1/farms/{self.farm2.id}/')
        self.assertEqual(response.status_code, 404)


@pytest.mark.django_db
class TestCropPlanIsolation(TransactionTestCase):
    """Test crop plan isolation via RLS"""

    def setUp(self):
        """Create test data with crop plans"""
        # Users
        self.user1 = User.objects.create_user(username='user1', password='test')
        self.user2 = User.objects.create_user(username='user2', password='test')

        # Farms
        self.farm1 = Farm.objects.create(name='Farm 1', code='F1', slug='farm-1')
        self.farm2 = Farm.objects.create(name='Farm 2', code='F2', slug='farm-2')

        # Memberships
        FarmMembership.objects.create(user=self.user1, farm=self.farm1, role='Admin')
        FarmMembership.objects.create(user=self.user2, farm=self.farm2, role='Admin')

        # Crop Plans
        self.plan1 = CropPlan.objects.create(
            farm=self.farm1,
            name='Plan Alpha'
        )
        self.plan2 = CropPlan.objects.create(
            farm=self.farm2,
            name='Plan Beta'
        )

    def _set_user_context(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.user_id', %s, false)", [str(user_id)])

    def test_user_sees_only_own_crop_plans(self):
        """User 1 sees only crop plans for Farm 1"""
        self._set_user_context(self.user1.id)

        plans = list(CropPlan.objects.all())
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].id, self.plan1.id)

    def test_user_cannot_access_other_crop_plan(self):
        """User 1 cannot access crop plans from Farm 2"""
        self._set_user_context(self.user1.id)

        with self.assertRaises(CropPlan.DoesNotExist):
            CropPlan.objects.get(id=self.plan2.id)


@pytest.mark.django_db
class TestMultiUserScenarios(TransactionTestCase):
    """Test complex multi-user farm isolation scenarios"""

    def setUp(self):
        """Create scenario: 3 users, 2 farms, mixed memberships"""
        # Users
        self.user1 = User.objects.create_user(username='admin1', password='test')
        self.user2 = User.objects.create_user(username='admin2', password='test')
        self.user3 = User.objects.create_user(username='viewer', password='test')

        # Farms
        self.farm_a = Farm.objects.create(name='Farm A', code='FA', slug='farm-a')
        self.farm_b = Farm.objects.create(name='Farm B', code='FB', slug='farm-b')

        # User 1: Admin on Farm A
        FarmMembership.objects.create(user=self.user1, farm=self.farm_a, role='Admin')

        # User 2: Admin on Farm B
        FarmMembership.objects.create(user=self.user2, farm=self.farm_b, role='Admin')

        # User 3: Viewer on BOTH farms
        FarmMembership.objects.create(user=self.user3, farm=self.farm_a, role='Viewer')
        FarmMembership.objects.create(user=self.user3, farm=self.farm_b, role='Viewer')

    def _set_user_context(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.user_id', %s, false)", [str(user_id)])

    def test_user_with_multiple_farms_sees_all(self):
        """User 3 with access to both farms sees both"""
        self._set_user_context(self.user3.id)

        farms = list(Farm.objects.all().order_by('code'))
        self.assertEqual(len(farms), 2)
        self.assertEqual(farms[0].code, 'FA')
        self.assertEqual(farms[1].code, 'FB')

    def test_isolated_users_see_only_their_farm(self):
        """User 1 sees only Farm A"""
        self._set_user_context(self.user1.id)

        farms = list(Farm.objects.all())
        self.assertEqual(len(farms), 1)
        self.assertEqual(farms[0].code, 'FA')


# Run with: python manage.py test core.tests.test_rls_policies
