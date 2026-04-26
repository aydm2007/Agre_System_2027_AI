from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from smart_agri.core.models import (
    Farm, Activity, Location, Item, ItemInventory, ItemInventoryBatch, 
    Unit, DailyLog, Crop, CropVariety, LocationTreeStock, TreeStockEvent, ActivityItem
)
from smart_agri.core.services.costing import calculate_activity_cost
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.core.services.tree_inventory import TreeInventoryService

class ForensicRemediationTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Forensic Farm")
        self.unit = Unit.objects.create(code="kg", name="Kilogram")
        self.item = Item.objects.create(name="Test Item", unit=self.unit, group="Input")
        self.location = Location.objects.create(name="Store 1", farm=self.farm)
        self.log = DailyLog.objects.create(farm=self.farm, log_date=timezone.now().date())

    def test_costing_fails_fast_on_missing_config(self):
        """Phase 1: Ensure costing raises ValueError if config is missing (No silent zero)."""
        # Create minimal activity
        activity = Activity.objects.create(
            name="Test Costing",
            log=self.log,
            planted_area=Decimal("10"),
            planted_uom='hectare'
        )
        
        # We expect validation error because CostConfiguration is missing for this farm
        with self.assertRaises(ValueError) as cm:
             calculate_activity_cost(activity)
        
        self.assertIn("Overhead rate configuration missing", str(cm.exception))

    def test_inventory_blocks_naked_writes_on_batched_item(self):
        """Phase 2: Use InventoryService to ensure no 'naked' writes if batches exist."""
        # 1. Create initial batch
        InventoryService.record_movement(
            farm=self.farm, item=self.item, qty_delta=Decimal("100"), 
            location=self.location, batch_number="BATCH-001"
        )
        
        # 2. Try to remove without batch
        # This causes 'Split Brain' (Inventory decreases, Batches stay same)
        # We remediated this to raise ValueError.
        with self.assertRaises(ValueError) as cm:
            InventoryService.record_movement(
                 farm=self.farm, item=self.item, qty_delta=Decimal("-10"),
                 location=self.location, batch_number=None
            )
        self.assertIn("tracked by batches", str(cm.exception))

    def test_tree_inventory_no_clamping(self):
        """Phase 3: Ensure tree stock update fails on negative result instead of clamping to 0."""
        crop = Crop.objects.create(name="Palm")
        variety = CropVariety.objects.create(name="Dates", crop=crop)
        
        # Setup stock with 5 trees
        stock = LocationTreeStock.objects.create(
             location=self.location, crop_variety=variety, current_tree_count=5
        )
        
        # Create an activity that supposedly added 10 trees (Delta +10)
        activity = Activity.objects.create(
            name="Planting", log=self.log, location=self.location, variety=variety,
            tree_count_delta=10
        )
        
        # Create the event manually to simulate history
        event = TreeStockEvent.objects.create(
            activity=activity,
            location_tree_stock=stock,
            tree_count_delta=10,
            resulting_tree_count=15 # Assume it was 5 before? No.
            # If current is 5, and we added 10... 
            # Wait, let's reverse.
        )
        
        # We want to reverse this event.
        # Reversing +10 means applying -10.
        # Stock Current = 5.
        # 5 - 10 = -5.
        # Old behavior: Clamped to 0.
        # New behavior: Raises ValidationError.
        
        service = TreeInventoryService()
        from django.core.exceptions import ValidationError
        
        with self.assertRaises(ValidationError):
            service.reverse_activity(activity=activity)
        
        stock.refresh_from_db()
        self.assertEqual(stock.current_tree_count, 5, "Stock should remain unchanged on failure")


class CAT001BulkCostsAtomicTests(TestCase):
    """
    Tests for CAT-001 Fix: calculate_bulk_costs atomic block fix.
    Verifies that all operations run inside transaction.atomic().
    """
    
    def setUp(self):
        from smart_agri.core.models import Task, LaborRate, MachineRate, CostConfiguration, Asset
        self.farm = Farm.objects.create(name="Bulk Cost Test Farm")
        self.location = Location.objects.create(name="Field A", farm=self.farm)
        self.log = DailyLog.objects.create(farm=self.farm, log_date=timezone.now().date())
        self.crop = Crop.objects.create(name="Test Crop")
        self.task = Task.objects.create(name="Test Task", crop=self.crop)
        
        # Create required rates
        LaborRate.objects.create(
            farm=self.farm, 
            role_name="Worker", 
            cost_per_hour=Decimal("50"),
            effective_date=timezone.now().date()
        )
        CostConfiguration.objects.create(
            farm=self.farm,
            overhead_rate_per_hectare=Decimal("100")
        )
    
    def test_bulk_costs_fails_atomically_on_missing_labor_rate(self):
        """CAT-001: Bulk cost calculation should fail fast if labor rate is missing."""
        from smart_agri.core.services.costing import calculate_bulk_costs
        from smart_agri.core.models import LaborRate
        
        # Create activity
        activity = Activity.objects.create(
            log=self.log,
            location=self.location,
            task=self.task,
            days_spent=Decimal("2"),
            planted_area=Decimal("5"),
            planted_uom='hectare'
        )
        
        # Remove labor rate to cause failure
        LaborRate.objects.filter(farm=self.farm).delete()
        
        # Attempt bulk calculation - should raise ValueError
        with self.assertRaises(ValueError) as cm:
            calculate_bulk_costs(Activity.objects.filter(pk=activity.pk))
        
        self.assertIn("Labor Rate missing", str(cm.exception))
        
        # Verify activity costs unchanged (atomic rollback)
        activity.refresh_from_db()
        self.assertEqual(activity.cost_total, Decimal("0"))
    
    def test_bulk_costs_updates_all_activities_atomically(self):
        """CAT-001: All activities should be updated atomically."""
        from smart_agri.core.services.costing import calculate_bulk_costs
        
        # Create multiple activities
        activities = []
        for i in range(3):
            act = Activity.objects.create(
                log=self.log,
                location=self.location,
                task=self.task,
                days_spent=Decimal("1"),
                planted_area=Decimal("1"),
                planted_uom='hectare'
            )
            activities.append(act)
        
        # Run bulk calculation
        updated_count = calculate_bulk_costs(
            Activity.objects.filter(pk__in=[a.pk for a in activities])
        )
        
        self.assertEqual(updated_count, 3)
        
        # Verify all were updated
        for act in activities:
            act.refresh_from_db()
            self.assertGreater(act.cost_total, Decimal("0"))


class CAT002InventoryConstraintTests(TestCase):
    """
    Tests for CAT-002 Fix: Inventory qty >= 0 CHECK constraint.
    """
    
    def setUp(self):
        self.farm = Farm.objects.create(name="Constraint Test Farm")
        self.unit = Unit.objects.create(code="L", name="Liter")
        self.item = Item.objects.create(name="Fuel", unit=self.unit, group="Material")
        self.location = Location.objects.create(name="Tank", farm=self.farm)
    
    def test_inventory_creation_with_zero_qty_succeeds(self):
        """CAT-002: Creating inventory with qty=0 should succeed."""
        inv = ItemInventory.objects.create(
            farm=self.farm,
            location=self.location,
            item=self.item,
            qty=Decimal("0")
        )
        self.assertEqual(inv.qty, Decimal("0"))
    
    def test_inventory_creation_with_positive_qty_succeeds(self):
        """CAT-002: Creating inventory with positive qty should succeed."""
        inv = ItemInventory.objects.create(
            farm=self.farm,
            location=self.location,
            item=self.item,
            qty=Decimal("100.5")
        )
        self.assertEqual(inv.qty, Decimal("100.5"))


class CAT004ServiceTypeTests(TestCase):
    """
    Tests for CAT-004 Fix: TreeServiceCoverage service_type constraint.
    """
    
    def setUp(self):
        from smart_agri.core.models import TreeServiceCoverage
        self.farm = Farm.objects.create(name="Service Type Test Farm")
        self.location = Location.objects.create(name="Orchard", farm=self.farm)
        self.crop = Crop.objects.create(name="Mango")
        self.variety = CropVariety.objects.create(name="Alphonso", crop=self.crop)
        self.log = DailyLog.objects.create(farm=self.farm, log_date=timezone.now().date())
        self.activity = Activity.objects.create(log=self.log, location=self.location)
    
    def test_all_service_types_accepted(self):
        """CAT-004: All 6 service types should be accepted by the database."""
        from smart_agri.core.models import TreeServiceCoverage
        
        service_types = ['general', 'irrigation', 'fertilization', 'pruning', 'pest_control', 'harvesting']
        
        for st in service_types:
            coverage = TreeServiceCoverage.objects.create(
                farm=self.farm,
                location=self.location,
                crop_variety=self.variety,
                activity=self.activity,
                service_type=st,
                trees_covered=10,
                area_covered_ha=Decimal("1"),
                cost_per_tree=Decimal("5")
            )
            self.assertEqual(coverage.service_type, st)
            coverage.delete()  # Clean up for next iteration

