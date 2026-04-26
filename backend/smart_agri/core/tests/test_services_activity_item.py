from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from smart_agri.core.models import Activity, ActivityItem, Item, Unit, Task, ItemInventory, Farm
from smart_agri.core.services.activity_item_service import ActivityItemService

User = get_user_model()

class ActivityItemServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.farm = Farm.objects.create(name='Test Farm', owner=self.user)
        self.unit = Unit.objects.create(code='KG', name='Kilogram')
        self.item = Item.objects.create(
            name='Test Item',
            group='Material',
            uom='kg',
            unit=self.unit,
            unit_price=Decimal('10.00')
        )
        self.task = Task.objects.create(name='Test Task')
        self.activity = Activity.objects.create(
            created_by=self.user,
            task=self.task,
            date='2023-01-01'
        )

    def test_create_item_updates_cost(self):
        qty = Decimal('5.00')
        expected_cost = qty * self.item.unit_price # 5 * 10 = 50

        ActivityItemService.create_item(self.activity, self.item, qty)

        self.activity.refresh_from_db()
        self.assertEqual(self.activity.cost_materials, expected_cost)
        self.assertEqual(self.activity.cost_total, expected_cost)

    def test_update_item_updates_cost(self):
        # Initial create
        item_obj = ActivityItemService.create_item(self.activity, self.item, Decimal('5.00'))
        
        # Update qty to 10
        new_qty = Decimal('10.00')
        expected_cost = new_qty * self.item.unit_price # 10 * 10 = 100

        ActivityItemService.update_item(item_obj, qty=new_qty)

        self.activity.refresh_from_db()
        self.assertEqual(self.activity.cost_materials, expected_cost)
        self.assertEqual(self.activity.cost_total, expected_cost)

    def test_delete_item_updates_cost(self):
        # Initial create
        item_obj = ActivityItemService.create_item(self.activity, self.item, Decimal('5.00'))
        self.activity.refresh_from_db()
        self.assertNotEqual(self.activity.cost_total, 0)

        # Delete
        ActivityItemService.delete_item(item_obj)

        self.activity.refresh_from_db()
        self.assertEqual(self.activity.cost_materials, Decimal('0.00'))
        self.assertEqual(self.activity.cost_total, Decimal('0.00'))
