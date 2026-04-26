from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.contrib.auth.models import Group, User

from smart_agri.core.models import (
    Farm,
    DailyLog,
    Location,
    Task,
    Item,
    ItemInventory,
    StockMovement,
    Crop,
)
from smart_agri.accounts.models import FarmMembership


class ActivityItemTests(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user('manager_items', password='pass', is_staff=True)
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        self.manager.groups.add(manager_group)

        self.farm = Farm.objects.create(name='farm-items', slug='farm-items', region='region')
        FarmMembership.objects.create(user=self.manager, farm=self.farm, role='مدير المزرعة')

        self.log = DailyLog.objects.create(farm=self.farm, log_date='2025-10-29')
        # create a location and a crop required by Task
        self.location = Location.objects.create(farm=self.farm, name='loc1', type='Field')
        crop = Crop.objects.create(name='test-crop', mode='Open')
        self.task = Task.objects.create(crop=crop, stage='stage', name='task', requires_tree_count=False)

        self.client = APIClient()
        self.client.force_authenticate(self.manager)
        self.url = reverse('activities-list')

    def test_create_activity_with_items_consumes_stock(self):
        item = Item.objects.create(name='Urea', group='fertilizer', uom='kg')
        ItemInventory.objects.create(farm=self.farm, location=self.location, item=item, qty=Decimal('10'), uom='kg')

        payload = {
            'log_id': self.log.id,
            'task_id': self.task.id,
            'location_ids': [self.location.id],
            'items': [
                {'item': item.id, 'qty': '3', 'uom': 'kg'},
            ],
        }

        response = self.client.post(self.url, payload, format='json', HTTP_X_IDEMPOTENCY_KEY='test-1')
        if response.status_code == 500:
            print("500 ERROR CONTENT:", response.content)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # StockMovement created
        movements = StockMovement.objects.filter(ref_type='activity', ref_id=str(response.data['id']))
        self.assertTrue(movements.exists())
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements.first().qty_delta, Decimal('-3'))

        # Inventory updated via signal
        inv = ItemInventory.objects.get(farm=self.farm, location=self.location, item=item)
        self.assertEqual(inv.qty, Decimal('7'))

    def test_create_activity_with_items_insufficient_stock_returns_400(self):
        item = Item.objects.create(name='Compost', group='material', uom='kg')
        ItemInventory.objects.create(farm=self.farm, location=self.location, item=item, qty=Decimal('1'), uom='kg')

        payload = {
            'log_id': self.log.id,
            'task_id': self.task.id,
            'location_ids': [self.location.id],
            'items': [
                {'item': item.id, 'qty': '5', 'uom': 'kg'},
            ],
        }

        response = self.client.post(self.url, payload, format='json', HTTP_X_IDEMPOTENCY_KEY='test-2')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_details = response.data.get('error', {}).get('details', {})
        if 'items' in error_details:
             self.assertIn('shortages', str(error_details['items']))
        else:
             self.assertIn('items', response.data)

    def test_update_activity_items_restock_on_replace(self):
        item = Item.objects.create(name='Fuel', group='consumable', uom='L')
        ItemInventory.objects.create(farm=self.farm, location=self.location, item=item, qty=Decimal('10'), uom='L')

        # Ensure log is same-day so updates are permitted
        from django.utils import timezone
        self.log.log_date = timezone.localdate()
        self.log.save(update_fields=['log_date'])

        payload = {
            'log_id': self.log.id,
            'task_id': self.task.id,
            'location_ids': [self.location.id],
            'items': [{'item': item.id, 'qty': '4', 'uom': 'L'}],
        }
        create_resp = self.client.post(self.url, payload, format='json', HTTP_X_IDEMPOTENCY_KEY='test-3')
        if create_resp.status_code == 500:
            print("500 ERROR CONTENT:", create_resp.content)
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

        inv = ItemInventory.objects.get(farm=self.farm, location=self.location, item=item)
        self.assertEqual(inv.qty, Decimal('6'))

        update_payload = {'items': []}
        update_resp = self.client.patch(
            reverse('activities-detail', args=[create_resp.data['id']]), update_payload, format='json', HTTP_X_IDEMPOTENCY_KEY='test-4'
        )
        self.assertEqual(update_resp.status_code, status.HTTP_200_OK)

        inv.refresh_from_db()
        self.assertEqual(inv.qty, Decimal('10'))
