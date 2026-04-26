import uuid
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Farm


class MembershipApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user('admin', password='pass123', email='admin@example.com')
        self.viewer = User.objects.create_user('viewer', password='pass123', email='viewer@example.com')
        self.target = User.objects.create_user('target', password='pass123', email='target@example.com')
        self.available = User.objects.create_user('ali', password='pass123', first_name='Ali', last_name='Hassan')

        self.farm = Farm.objects.create(name='Alpha Farm', slug='alpha', region='North')
        self.foreign_farm = Farm.objects.create(name='Beta Farm', slug='beta', region='South')

        FarmMembership.objects.create(user=self.admin, farm=self.farm, role='مدير المزرعة')
        FarmMembership.objects.create(user=self.viewer, farm=self.farm, role='مشاهد')
        FarmMembership.objects.create(user=self.target, farm=self.foreign_farm, role='مشرف ميداني')

        self.client.force_authenticate(self.admin)

    def _results(self, response):
        data = response.json()
        return data.get('results', data)

    def test_list_returns_only_farms_user_can_access(self):
        resp = self.client.get('/api/v1/memberships/')
        self.assertEqual(resp.status_code, 200)
        farm_ids = {item['farm_id'] for item in self._results(resp)}
        self.assertEqual(farm_ids, {self.farm.id})

    def test_admin_can_add_membership(self):
        payload = {
            'farm': self.farm.id,
            'user': self.target.id,
            'role': 'مشرف ميداني',
        }
        resp = self.client.post('/api/v1/memberships/', payload, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(FarmMembership.objects.filter(user=self.target, farm=self.farm).exists())

    def test_viewer_cannot_add_membership(self):
        self.client.force_authenticate(self.viewer)
        payload = {
            'farm': self.farm.id,
            'user': self.target.id,
            'role': 'مشاهد',
        }
        resp = self.client.post('/api/v1/memberships/', payload, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        self.assertEqual(resp.status_code, 403)

    def test_cannot_remove_last_admin(self):
        membership = FarmMembership.objects.get(user=self.admin, farm=self.farm)
        resp = self.client.delete(f'/api/v1/memberships/{membership.id}/', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(FarmMembership.objects.filter(id=membership.id).exists())

    def test_available_users_excludes_existing_members(self):
        resp = self.client.get('/api/v1/memberships/available-users/', {'farm': self.farm.id, 'q': 'a'})
        self.assertEqual(resp.status_code, 200)
        usernames = {item['username'] for item in self._results(resp)}
        self.assertIn('ali', usernames)
        self.assertNotIn('admin', usernames)
        self.assertNotIn('viewer', usernames)

    def test_admin_can_update_role(self):
        membership = FarmMembership.objects.create(user=self.target, farm=self.farm, role='مشاهد')
        resp = self.client.patch(f'/api/v1/memberships/{membership.id}/', {'role': 'مدير المزرعة'}, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        self.assertEqual(resp.status_code, 200)
        membership.refresh_from_db()
        self.assertEqual(membership.role, 'مدير المزرعة')

    def test_admin_cannot_downgrade_last_admin(self):
        member = FarmMembership.objects.get(user=self.admin, farm=self.farm)
        resp = self.client.patch(f'/api/v1/memberships/{member.id}/', {'role': 'مشاهد'}, format='json', HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        self.assertEqual(resp.status_code, 400)
        member.refresh_from_db()
        self.assertEqual(member.role, 'مدير المزرعة')

