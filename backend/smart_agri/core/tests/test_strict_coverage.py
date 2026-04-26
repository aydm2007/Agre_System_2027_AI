from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from smart_agri.core.models import Farm, Location, Item, Unit, ItemInventory, DailyLog, Activity
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.core.services.costing import _get_overhead_rate, _get_machine_rate
import uuid

class TestStrictInventory(TestCase):
    def test_negative_stock_prevention(self):
        """Test that withdrawing more than available raises ValidationError."""
        farm = Farm.objects.create(name='Test Farm', slug='test-farm')
        item = Item.objects.create(name='Test Item', uom='kg')
        location = Location.objects.create(farm=farm, name='Store A')
        
        # Initial Stock: 10
        InventoryService.record_movement(farm, item, Decimal('10'), location)
        
        # Withdraw 15 -> Should fail
        with self.assertRaisesMessage(ValidationError, "الرصيد غير كافي"):
            InventoryService.record_movement(farm, item, Decimal('-15'), location)
        

    def test_cross_farm_contamination_prevention(self):
        """Test that using a location from another farm raises ValidationError."""
        farm1 = Farm.objects.create(name='Farm 1', slug='farm-1')
        farm2 = Farm.objects.create(name='Farm 2', slug='farm-2')
        location2 = Location.objects.create(farm=farm2, name='Farm 2 Loc')
        item = Item.objects.create(name='Test Item', uom='kg')
        
        with self.assertRaisesMessage(ValidationError, "انتهاك أمني"):
            InventoryService.record_movement(farm1, item, Decimal('10'), location2)
        

class TestStrictCosting(TestCase):
    def test_orphan_farm_overhead(self):
        """Test that overhead calculation fails for orphan activities (no farm)."""
        with self.assertRaisesMessage(ValidationError, "نشاط يتيم"):
            _get_overhead_rate(None)
        

    def test_missing_machine_rate(self):
        """Test that using a machine without a rate raises error."""
        # Note: We pass an ID that doesn't exist or has no rate
        with self.assertRaises(ValidationError):
            _get_machine_rate(99999) 
