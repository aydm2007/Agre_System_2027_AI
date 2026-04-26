from decimal import Decimal
from django.test import TransactionTestCase, TestCase
from django.utils import timezone
from smart_agri.core.models import (
    Farm, Activity, Location, Item, ItemInventory, ItemInventoryBatch, 
    Unit, DailyLog, Crop, CropVariety, LocationTreeStock, TreeStockEvent, ActivityItem,
    StockMovement, CostConfiguration, LaborRate, MachineRate, Asset
)
from smart_agri.core.services.costing import calculate_activity_cost
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.core.services.tree_inventory import TreeInventoryService

class ForensicIntegrationTests(TransactionTestCase):
    # Use TransactionTestCase to test DB Transaction logic although we can't fully simulate concurrency here easily.
    # We focus on "Double Write" and "Fail Fast".

    def setUp(self):
        self.farm = Farm.objects.create(name="Forensic Farm", slug="forensic-farm")
        self.unit = Unit.objects.create(code="kg", name="Kilogram")
        self.item = Item.objects.create(name="Test Item", unit=self.unit, group="Input")
        self.location = Location.objects.create(name="Store 1", farm=self.farm, type="store", code="S1")
        self.log = DailyLog.objects.create(farm=self.farm, log_date=timezone.now().date())

    def test_inventory_no_double_write(self):
        """
        Verify that recording a movement via InventoryService does NOT double-increment inventory.
        
        NOTE: In a real DB with the Trigger installed, 
        InventoryService.record_movement() -> Creates StockMovement -> Trigger Fired -> ItemInventory Updated.
        Python Code -> Should NOT update ItemInventory again.
        
        Since we are in a Test DB (SQLite usually, or Postgres without migration triggers unless applied),
        we might not have the trigger active in this test environment depending on how `workspace_v3.1.1.8.8.1.sql` was loaded.
        
        IF the trigger is NOT present in the test DB, the ItemInventory will remain 0 (because we removed Python update).
        This confirms we successfully removed the Python update.
        
        IF the trigger IS present, it will be Correct (Delta only).
        
        So asserting it is 0 (if no trigger) or Delta (if trigger) confirms we removed double write.
        If double write was still there, and trigger was missing, it would be Delta.
        
        Wait, if we removed Python update, and trigger is missing, result is 0.
        If we retained Python update, and trigger is missing, result is Delta.
        
        We want to prove we removed Python update. So we expect 0 in a trigger-less environment.
        """
        
        # 1. Record Movement
        InventoryService.record_movement(
            farm=self.farm, item=self.item, qty_delta=Decimal("10"), 
            location=self.location
        )
        
        # 2. Check Inventory
        inv = ItemInventory.objects.filter(farm=self.farm, item=self.item).first()
        
        # If we successfully removed the write from Python, this might be None or 0 
        # (assuming we run tests without the raw SQL dump applied).
        # We just want to check that python logic didn't do it.
        # But wait, we added logic to CREATE it with 0 if missing.
        
        if inv:
            # It should be 0 because we passed Decimal("0") to create().
            self.assertEqual(inv.qty, Decimal("0"), "Inventory should be 0 because tests lack the Release DB Trigger")
        else:
            # If not created (because we only create if missing, and logic was slightly conditional?)
            # Actually our code creates it if missing.
            pass

    def test_costing_fails_fast_missing_config(self):
        """Ensure failure when overhead config is missing (No defaults)."""
        activity = Activity.objects.create(
            name="Test Costing",
            log=self.log,
            planted_area=Decimal("10"),
            planted_uom='hectare'
        )
        
        with self.assertRaises(ValueError) as cm:
             calculate_activity_cost(activity)
        self.assertIn("Overhead rate not configured", str(cm.exception))

    def test_costing_fails_fast_missing_labor_rate(self):
        """Ensure failure when labor rate is missing."""
        # 1. Config Overhead (Pass first check)
        CostConfiguration.objects.create(farm=self.farm, overhead_rate_per_hectare=Decimal("10"))
        
        activity = Activity.objects.create(
                name="Test Costing", log=self.log, days_spent=Decimal("5")
        )
        
        with self.assertRaises(ValueError) as cm:
             calculate_activity_cost(activity)
        self.assertIn("No effective LaborRate", str(cm.exception))
