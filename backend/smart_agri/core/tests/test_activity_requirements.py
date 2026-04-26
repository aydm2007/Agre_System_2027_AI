from datetime import date
from unittest.mock import patch
import uuid

from django.contrib.auth.models import Group, Permission, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from smart_agri.core.models import (
    Activity,
    Asset,
    Crop,
    CropProduct,
    CropVariety,
    DailyLog,
    Farm,
    Item,
    Location,
    Task,
    TreeLossReason,
)
from smart_agri.accounts.models import FarmMembership


class ActivityRequirementTests(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user('manager', password='pass', is_staff=True)
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        self.manager.groups.add(manager_group)

        self.farm = Farm.objects.create(name='المزرعة الأولى', slug='farm-1', region='الوسطى')
        FarmMembership.objects.create(user=self.manager, farm=self.farm, role='Manager')

        self.log = DailyLog.objects.create(farm=self.farm, log_date=date.today())
        self.crop = Crop.objects.create(name='طماطم', mode='Open')
        self.location = Location.objects.create(farm=self.farm, name='الموقع الرئيسي', type='Field')
        self.asset = Asset.objects.create(farm=self.farm, name='حفار', category='Machinery')

        self.client = APIClient()
        self.client.force_authenticate(self.manager)
        self.url = reverse('activities-list')

        tree_sync = patch('smart_agri.core.api.TreeInventoryService.reconcile_activity', return_value=None)
        self.mock_tree_sync = tree_sync.start()
        self.addCleanup(tree_sync.stop)

    def _payload(self, **overrides):
        base = {
            'log_id': self.log.id,
            'crop_id': self.crop.id,
            'task_id': None,
            'location_id': self.location.id,
            'location_ids': [self.location.id],
            'asset_id': None,
            'days_spent': '1.5',
        }
        base.update(overrides)
        return base

    def _error_details(self, response):
        return response.data.get('error', {}).get('details', response.data)

    def _post(self, payload):
        return self.client.post(
            self.url,
            payload,
            format='json',
            HTTP_X_IDEMPOTENCY_KEY=f'activity-requirements-{uuid.uuid4()}',
        )

    def _create_tree_activity_context(self, **task_overrides):
        tree_crop = Crop.objects.create(name='نخيل', mode='Open', is_perennial=True)
        variety = CropVariety.objects.create(crop=tree_crop, name='سكري')
        harvest_item = Item.objects.create(name='تمور سكري', group='Harvested Product', uom='kg')
        crop_product = CropProduct.objects.create(crop=tree_crop, item=harvest_item)
        task_data = {
            'crop': tree_crop,
            'stage': 'أشجار',
            'name': 'رعاية الأشجار',
            'requires_tree_count': True,
            'is_perennial_procedure': True,
        }
        task_data.update(task_overrides)
        task = Task.objects.create(**task_data)
        return tree_crop, variety, task, crop_product

    def test_requires_well_reading_enforced(self):
        task = Task.objects.create(
            crop=self.crop,
            stage='ري',
            name='تشغيل البئر',
            requires_well=True,
        )
        response = self._post(self._payload(task_id=task.id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('well_reading', self._error_details(response))

    def test_skip_well_permission_allows_missing_reading(self):
        task = Task.objects.create(
            crop=self.crop,
            stage='ري',
            name='تشغيل البئر',
            requires_well=True,
        )
        perm = Permission.objects.get(codename='skip_well_reading')
        self.manager.user_permissions.add(perm)
        response = self._post(self._payload(task_id=task.id))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Activity.objects.filter(id=response.data['id']).exists())

    def test_machinery_fields_required(self):
        task = Task.objects.create(
            crop=self.crop,
            stage='حصاد',
            name='تشغيل الآلة',
            requires_machinery=True,
        )
        response = self._post(self._payload(task_id=task.id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        details = self._error_details(response)
        self.assertIn('asset_id', details)
        self.assertIn('machine_hours', details)

        valid_payload = self._payload(
            task_id=task.id,
            asset_id=self.asset.id,
            machine_hours='2',
            machine_meter_reading='1500',
            fuel_consumed='12',
        )
        response = self._post(valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Activity.objects.filter(id=response.data['id']).exists())

    def test_legacy_client_cost_fields_are_ignored_before_decimal_validation(self):
        task = Task.objects.create(
            crop=self.crop,
            stage='رعاية',
            name='نشاط الكل - مانجو',
        )
        payload = self._payload(
            task_id=task.id,
            cost_materials='12.1234567',
            cost_total='13.9999999',
        )

        response = self._post(payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        activity = Activity.objects.get(id=response.data['id'])
        self.assertEqual(activity.cost_materials, 0)
        self.assertEqual(activity.cost_total, 0)

    def test_tree_loss_reason_required_for_negative_delta(self):
        tree_crop, variety, task, _ = self._create_tree_activity_context()
        payload = self._payload(
            crop_id=tree_crop.id,
            task_id=task.id,
            variety_id=variety.id,
            activity_tree_count=120,
            tree_count_delta=-5,
        )
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        details = self._error_details(response)
        self.assertIn('tree_loss_reason_id', details)
        self.assertEqual(
            details['tree_loss_reason_id'][0],
            'يجب اختيار سبب الفقد عند تسجيل خسارة.',
        )

    def test_tree_harvest_requires_quantity(self):
        tree_crop, variety, task, crop_product = self._create_tree_activity_context(is_harvest_task=True)
        payload = self._payload(
            crop_id=tree_crop.id,
            task_id=task.id,
            variety_id=variety.id,
            activity_tree_count=80,
            tree_count_delta=0,
            product_id=crop_product.id,
        )
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        details = self._error_details(response)
        self.assertIn('harvest_quantity', details)
        self.assertEqual(
            details['harvest_quantity'][0],
            'كمية الحصاد مطلوبة لهذا النشاط.',
        )

    def test_tree_harvest_accepts_required_fields(self):
        tree_crop, variety, task, crop_product = self._create_tree_activity_context(is_harvest_task=True)
        loss_reason = TreeLossReason.objects.create(
            code='pest',
            name_en='Pest',
            name_ar='آفات',
        )
        payload = self._payload(
            crop_id=tree_crop.id,
            task_id=task.id,
            variety_id=variety.id,
            activity_tree_count=90,
            tree_count_delta=-3,
            tree_loss_reason_id=loss_reason.id,
            harvest_quantity='150',
            product_id=crop_product.id,
        )
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        activity = Activity.objects.get(id=response.data['id'])
        self.assertEqual(activity.tree_loss_reason_id, loss_reason.id)
        self.assertIsNotNone(getattr(activity, 'harvest_quantity', None) or getattr(activity.harvest_details, 'harvest_quantity', None))
        self.assertEqual(activity.product_id, crop_product.id)

    def test_harvest_auto_creates_crop_product_from_item(self):
        tree_crop = Crop.objects.create(name='نخيل', mode='Open', is_perennial=True)
        variety = CropVariety.objects.create(crop=tree_crop, name='سكري')
        harvest_item = Item.objects.create(name='تمر سكري', group='Harvested Product', uom='kg')
        task = Task.objects.create(
            crop=tree_crop,
            stage='حصاد',
            name='حصاد يومي',
            requires_tree_count=True,
            is_perennial_procedure=True,
            is_harvest_task=True,
        )

        payload = self._payload(
            crop_id=tree_crop.id,
            task_id=task.id,
            variety_id=variety.id,
            activity_tree_count=40,
            tree_count_delta=0,
            harvest_quantity='75',
            product_id=harvest_item.id,
        )

        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        activity = Activity.objects.get(id=response.data['id'])
        self.assertIsNotNone(activity.product)
        self.assertEqual(activity.product.item_id, harvest_item.id)
        self.assertEqual(activity.product.crop_id, tree_crop.id)
        self.assertEqual(activity.product.farm_id, self.farm.id)
