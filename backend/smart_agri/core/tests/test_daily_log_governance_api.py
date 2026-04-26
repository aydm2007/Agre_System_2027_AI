from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import (
    Activity,
    ActivityItem,
    ActivityLocation,
    Crop,
    CropVariety,
    DailyLog,
    Farm,
    FarmCrop,
    Item,
    Location,
    LocationTreeStock,
    Task,
)


class DailyLogGovernanceAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('governance_user', password='pass', is_staff=True)
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        self.user.groups.add(manager_group)

        self.farm = Farm.objects.create(name='Farm Governance', slug='farm-governance', region='A')
        FarmMembership.objects.create(user=self.user, farm=self.farm, role='Manager')

        self.crop = Crop.objects.create(name='Mango', mode='Open', is_perennial=True)
        FarmCrop.objects.create(farm=self.farm, crop=self.crop)

        self.location_a = Location.objects.create(name='Zone A', farm=self.farm)
        self.location_b = Location.objects.create(name='Zone B', farm=self.farm)

        self.variety_shared = CropVariety.objects.create(crop=self.crop, name='Keitt')
        self.variety_location_a = CropVariety.objects.create(crop=self.crop, name='Kent')
        self.variety_new = CropVariety.objects.create(crop=self.crop, name='Naomi')
        self.variety_zero_stock = CropVariety.objects.create(crop=self.crop, name='Zero Stock')
        self.variety_deleted = CropVariety.objects.create(crop=self.crop, name='Legacy')
        CropVariety.objects.filter(pk=self.variety_deleted.pk).update(deleted_at=timezone.now())

        LocationTreeStock.objects.create(
            location=self.location_a,
            crop_variety=self.variety_shared,
            current_tree_count=10,
        )
        LocationTreeStock.objects.create(
            location=self.location_b,
            crop_variety=self.variety_shared,
            current_tree_count=8,
        )
        LocationTreeStock.objects.create(
            location=self.location_a,
            crop_variety=self.variety_location_a,
            current_tree_count=5,
        )
        LocationTreeStock.objects.create(
            location=self.location_b,
            crop_variety=self.variety_zero_stock,
            current_tree_count=0,
        )

        self.task = Task.objects.create(
            crop=self.crop,
            stage='Control',
            name='Tree Service',
            requires_tree_count=True,
            is_perennial_procedure=True,
        )
        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date=date.today(),
            status=DailyLog.STATUS_DRAFT,
            created_by=self.user,
        )
        self.activity = Activity.objects.create(
            log=self.log,
            crop=self.crop,
            task=self.task,
            crop_variety=self.variety_shared,
            cost_total=Decimal('10.0000'),
            created_by=self.user,
        )
        ActivityLocation.objects.create(activity=self.activity, location=self.location_a, allocated_percentage=Decimal('50.00'))
        ActivityLocation.objects.create(activity=self.activity, location=self.location_b, allocated_percentage=Decimal('50.00'))

        self.client = APIClient()
        self.client.force_authenticate(self.user)

        inventory_patch = patch(
            'smart_agri.inventory.services.InventoryService.record_movement',
            return_value=None,
        )
        self.mock_inventory_movement = inventory_patch.start()
        self.addCleanup(inventory_patch.stop)

    def test_crop_varieties_endpoint_returns_farm_scoped_active_varieties(self):
        response = self.client.get(
            reverse('crop-varieties-list'),
            {'crop_id': self.crop.id, 'farm_id': self.farm.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data.get('results', response.data)
        names = [entry['name'] for entry in payload]

        self.assertIn('Keitt', names)
        self.assertIn('Kent', names)
        self.assertIn('Naomi', names)
        self.assertNotIn('Legacy', names)

    def test_crop_varieties_endpoint_is_location_aware_for_union_coverage(self):
        response = self.client.get(
            reverse('crop-varieties-list'),
            {
                'crop_id': self.crop.id,
                'farm_id': self.farm.id,
                'location_ids': f'{self.location_a.id},{self.location_b.id}',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data.get('results', response.data)
        names = [entry['name'] for entry in payload]

        self.assertEqual(names, ['Keitt', 'Kent'])
        shared = next(entry for entry in payload if entry['name'] == 'Keitt')
        partial = next(entry for entry in payload if entry['name'] == 'Kent')
        self.assertTrue(shared['available_in_all_locations'])
        self.assertEqual(shared['location_ids'], [self.location_a.id, self.location_b.id])
        self.assertEqual(shared['current_tree_count_total'], 18)
        self.assertEqual(
            shared['current_tree_count_by_location'],
            {str(self.location_a.id): 10, str(self.location_b.id): 8},
        )
        self.assertFalse(partial['available_in_all_locations'])
        self.assertEqual(partial['location_ids'], [self.location_a.id])
        self.assertEqual(partial['current_tree_count_total'], 5)
        self.assertEqual(partial['current_tree_count_by_location'], {str(self.location_a.id): 5})
        self.assertNotIn('Zero Stock', names)

    def test_crop_varieties_endpoint_excludes_zero_stock_varieties_from_selected_locations(self):
        response = self.client.get(
            reverse('crop-varieties-list'),
            {
                'crop_id': self.crop.id,
                'farm_id': self.farm.id,
                'location_ids': str(self.location_b.id),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data.get('results', response.data)
        self.assertEqual([entry['name'] for entry in payload], ['Keitt'])
        self.assertEqual(payload[0]['location_ids'], [self.location_b.id])
        self.assertEqual(
            payload[0]['current_tree_count_by_location'],
            {str(self.location_b.id): 8},
        )

    def test_activity_detail_prioritizes_varieties_available_in_all_selected_locations(self):
        response = self.client.get(reverse('activities-detail', args=[self.activity.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        varieties = response.data['available_varieties_by_location']
        self.assertEqual(varieties[0]['name'], 'Keitt')
        self.assertTrue(varieties[0]['available_in_all_locations'])
        self.assertEqual(sorted(varieties[0]['location_ids']), [self.location_a.id, self.location_b.id])

        self.assertEqual(varieties[1]['name'], 'Kent')
        self.assertFalse(varieties[1]['available_in_all_locations'])
        self.assertEqual(varieties[1]['location_ids'], [self.location_a.id])

    def test_activity_and_log_detail_expose_material_governance_flags(self):
        tracked_item = Item.objects.create(
            name='Fungicide',
            group='Pesticides',
            uom='L',
            unit_price=Decimal('0.0000'),
            requires_batch_tracking=True,
        )
        ActivityItem.objects.create(
            activity=self.activity,
            item=tracked_item,
            qty=Decimal('2.000'),
            uom='L',
            batch_number='',
            cost_per_unit=Decimal('0.0000'),
        )

        activity_response = self.client.get(reverse('activities-detail', args=[self.activity.id]))
        self.assertEqual(activity_response.status_code, status.HTTP_200_OK)
        self.assertTrue(activity_response.data['material_governance_blocked'])
        self.assertIn('material_governance_blocked', activity_response.data['governance_flags'])
        self.assertEqual(len(activity_response.data['item_governance_flags']), 1)
        self.assertIn(
            'missing_batch_tracking',
            activity_response.data['item_governance_flags'][0]['flags'],
        )

        log_response = self.client.get(reverse('dailylogs-detail', args=[self.log.id]))
        self.assertEqual(log_response.status_code, status.HTTP_200_OK)
        self.assertTrue(log_response.data['material_governance_blocked'])
        self.assertTrue(log_response.data['missing_price_governance'])
        self.assertGreaterEqual(len(log_response.data['material_governance_reasons']), 1)
