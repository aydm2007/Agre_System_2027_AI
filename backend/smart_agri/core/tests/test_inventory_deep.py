from django.test import TestCase
from django.db import transaction
from smart_agri.core.models import Item, Farm, Location, Unit, ItemInventory
from smart_agri.core.services.inventory_service import InventoryService
from decimal import Decimal

class InventoryDeepIntegrationTest(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Test Farm", total_area=100)
        self.store_loc = Location.objects.create(farm=self.farm, name="Main Store", short_code="STR")
        self.field_loc = Location.objects.create(farm=self.farm, name="Field 1", short_code="F1")
        self.unit = Unit.objects.create(code="kg", name="Kilogram")
        self.item = Item.objects.create(name="Fertilizer A", uom="kg", unit=self.unit, unit_price=Decimal("10.00")) # Initial Price 10

    def test_grn_updates_moving_average_price(self):
        """Test that GRN updates MAP correctly."""
        # Initial Stock: 0
        
        # 1. Receive 100 units @ 10 (Matches initial, should stay 10)
        InventoryService.process_grn(self.farm, self.item, self.store_loc, Decimal("100"), Decimal("10.00"), "GRN01")
        self.item.refresh_from_db()
        self.assertEqual(self.item.unit_price, Decimal("10.00"))
        
        # 2. Receive 100 units @ 20 (Price doubles)
        # Old Value: 100 * 10 = 1000
        # New Value: 100 * 20 = 2000
        # Total Qty: 200. Total Value: 3000. New Price: 15.
        InventoryService.process_grn(self.farm, self.item, self.store_loc, Decimal("100"), Decimal("20.00"), "GRN02")
        self.item.refresh_from_db()
        self.assertAlmostEqual(self.item.unit_price, Decimal("15.00"), places=2)
        
        # Verify Stock
        stock = InventoryService.get_stock_level(self.farm, self.item, self.store_loc)
        self.assertEqual(stock, Decimal("200.00"))

    def test_stock_transfer_atomicity(self):
        """Test moving stock from Store to Field."""
        # Setup stock
        InventoryService.process_grn(self.farm, self.item, self.store_loc, Decimal("100"), Decimal("10.00"), "GRN-INIT")
        
        # Transfer 50
        InventoryService.transfer_stock(self.farm, self.item, self.store_loc, self.field_loc, Decimal("50"), None)
        
        # Check Source
        stock_source = InventoryService.get_stock_level(self.farm, self.item, self.store_loc)
        self.assertEqual(stock_source, Decimal("50.00"))
        
        # Check Dest
        stock_dest = InventoryService.get_stock_level(self.farm, self.item, self.field_loc)
        self.assertEqual(stock_dest, Decimal("50.00"))
