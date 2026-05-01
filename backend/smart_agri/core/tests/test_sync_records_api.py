from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Farm, SyncRecord


def _get_results(data):
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


class SyncRecordAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.manager_group, _ = Group.objects.get_or_create(name='Manager')

        self.farm_alpha = Farm.objects.create(name='Farm Alpha', slug='farm-alpha', region='North')
        self.farm_beta = Farm.objects.create(name='Farm Beta', slug='farm-beta', region='South')

        self.manager = User.objects.create_user('manager', password='pass123')
        self.manager.groups.add(self.manager_group)
        FarmMembership.objects.create(user=self.manager, farm=self.farm_alpha, role='Manager')

        self.worker = User.objects.create_user('worker', password='pass123')
        FarmMembership.objects.create(user=self.worker, farm=self.farm_alpha, role='DataEntry')

        self.other_user = User.objects.create_user('observer', password='pass123')
        FarmMembership.objects.create(user=self.other_user, farm=self.farm_beta, role='Supervisor')

        self.manager_record = SyncRecord.objects.create(
            user=self.manager,
            farm=self.farm_alpha,
            category=SyncRecord.CATEGORY_DAILY_LOG,
            reference='ref-manager',
            status=SyncRecord.STATUS_SUCCESS,
        )
        self.worker_same_farm_record = SyncRecord.objects.create(
            user=self.worker,
            farm=self.farm_alpha,
            category=SyncRecord.CATEGORY_DAILY_LOG,
            reference='ref-worker-1',
            status=SyncRecord.STATUS_PENDING,
        )
        self.worker_other_farm_record = SyncRecord.objects.create(
            user=self.worker,
            farm=self.farm_beta,
            category=SyncRecord.CATEGORY_DAILY_LOG,
            reference='ref-worker-2',
            status=SyncRecord.STATUS_FAILED,
        )
        self.observer_record = SyncRecord.objects.create(
            user=self.other_user,
            farm=self.farm_beta,
            category=SyncRecord.CATEGORY_HTTP,
            reference='ref-observer',
            status=SyncRecord.STATUS_PENDING,
        )

    def test_manager_sees_own_and_member_farm_records(self):
        self.client.force_authenticate(self.manager)
        response = self.client.get('/api/v1/sync-records/')
        self.assertEqual(response.status_code, 200)
        payload = _get_results(response.json())
        returned_ids = {entry['id'] for entry in payload}
        self.assertIn(self.manager_record.id, returned_ids)
        self.assertIn(self.worker_same_farm_record.id, returned_ids)
        self.assertNotIn(self.observer_record.id, returned_ids)

    def test_non_manager_only_sees_own_records(self):
        self.client.force_authenticate(self.worker)
        response = self.client.get('/api/v1/sync-records/')
        self.assertEqual(response.status_code, 200)
        payload = _get_results(response.json())
        returned_ids = {entry['id'] for entry in payload}
        self.assertSetEqual(returned_ids, {self.worker_same_farm_record.id, self.worker_other_farm_record.id})

    def test_cannot_create_record_for_unowned_farm(self):
        self.client.force_authenticate(self.worker)
        payload = {
            'farm': self.farm_beta.id,
            'category': SyncRecord.CATEGORY_DAILY_LOG,
            'reference': 'ref-illegal',
            'status': SyncRecord.STATUS_PENDING,
        }
        response = self.client.post(
            '/api/v1/sync-records/',
            payload,
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='sync-records-illegal-ref',
        )
        self.assertIn(response.status_code, (400, 403))
        self.assertFalse(SyncRecord.objects.filter(reference='ref-illegal').exists())

    def test_exclude_demo_filters_demo_sync_records(self):
        SyncRecord.objects.create(
            user=self.manager,
            farm=self.farm_alpha,
            category=SyncRecord.CATEGORY_DAILY_LOG,
            reference='demo-offline-pending',
            status=SyncRecord.STATUS_PENDING,
            payload={'demo_fixture': True},
        )
        self.client.force_authenticate(self.manager)
        response = self.client.get('/api/v1/sync-records/?exclude_demo=1')
        self.assertEqual(response.status_code, 200)
        payload = _get_results(response.json())
        references = {entry['reference'] for entry in payload}
        self.assertNotIn('demo-offline-pending', references)
