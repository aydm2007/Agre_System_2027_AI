from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from smart_agri.core.models import Item, Unit, Farm, ItemInventory, StockMovement
from smart_agri.core.services.inventory_service import InventoryService

User = get_user_model()

class InventoryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='invuser', password='password')
        self.farm = Farm.objects.create(name='Inv Farm', owner=self.user)
        self.unit = Unit.objects.create(code='L', name='Liter')
        self.item = Item.objects.create(
            name='Diesel',
            group='Fuel',
            uom='L',
            unit=self.unit,
            unit_price=Decimal('2.50')
        )

    def test_record_movement_and_get_stock(self):
        # 1. Initial State
        initial_stock = InventoryService.get_stock_level(self.farm, self.item)
        self.assertEqual(initial_stock, Decimal('0'))

        # 2. Stock In
        qty_in = Decimal('100.00')
        InventoryService.record_movement(self.farm, self.item, qty_in, ref_type="PO", ref_id="PO-1")
        
        # Verify
        stock_after_in = InventoryService.get_stock_level(self.farm, self.item)
        self.assertEqual(stock_after_in, qty_in)
        
        inv = ItemInventory.objects.get(farm=self.farm, item=self.item)
        self.assertEqual(inv.qty, qty_in)

        # 3. Stock Out
        qty_out = Decimal('-20.00')
        InventoryService.record_movement(self.farm, self.item, qty_out, ref_type="Usage", ref_id="ACT-1")

        # Verify
        expected_stock = Decimal('80.00')
        stock_after_out = InventoryService.get_stock_level(self.farm, self.item)
        self.assertEqual(stock_after_out, expected_stock)

    def test_record_movement_signals_integration(self):
        """
        Verifies that StockMovement creation triggers the underlying signal logic
        that updates ItemInventory.
        """
        qty = Decimal('50.00')
        InventoryService.record_movement(self.farm, self.item, qty)
        
        self.assertTrue(ItemInventory.objects.filter(farm=self.farm, item=self.item).exists())
        self.assertEqual(ItemInventory.objects.get(farm=self.farm, item=self.item).qty, qty)
