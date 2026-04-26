"""
Forensic Audit Verification Tests
==================================
Tests to verify critical fixes from forensic audit remediation.

CRIT-001: Verify no double counting in inventory management
HIGH-002: Verify costing handles missing assets gracefully
"""
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from smart_agri.core.models import (
    Farm, Item, Unit, ItemInventory, StockMovement,
    Crop, Task, DailyLog, Activity, Location
)
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.core.services.costing import _get_machine_rate


User = get_user_model()


class ForensicAuditInventoryTests(TransactionTestCase):
    """
    CRIT-001: Verify that StockMovement INSERT does not cause double counting.
    
    The DB trigger `core_stockmovement_after_insert` manages `qty` in ItemInventory.
    Python code should NOT also update qty - it should only handle batches.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(username='forensic_user', password='p')
        self.farm = Farm.objects.create(name='Forensic Farm', slug='forensic', region='A')
        self.unit = Unit.objects.create(code='kg_forensic', name='Kilogram', symbol='kg', category='mass')
        self.item = Item.objects.create(
            name='Forensic Test Item',
            group='Test',
            uom='kg',
            unit=self.unit,
            unit_price=Decimal('10.00')
        )
    
    def test_single_movement_no_double_counting(self):
        """
        Critical: When a StockMovement is created, qty should increase by delta ONCE.
        If both trigger and Python update qty, it would be 2x delta (double counting).
        """
        # Initial state
        initial_qty = self._get_inventory_qty()
        self.assertEqual(initial_qty, Decimal('0'))
        
        # Record a movement
        delta = Decimal('100.00')
        InventoryService.record_movement(
            farm=self.farm,
            item=self.item,
            qty_delta=delta,
            ref_type='forensic_test',
            ref_id='FT-001'
        )
        
        # Verify qty increased by exactly delta, not 2*delta
        final_qty = self._get_inventory_qty()
        
        self.assertEqual(
            final_qty - initial_qty,
            delta,
            f"DOUBLE COUNTING DETECTED! Expected qty increase of {delta}, "
            f"but got {final_qty - initial_qty}. "
            "Check that Python is not also updating qty alongside the DB trigger."
        )
    
    def test_multiple_movements_accumulate_correctly(self):
        """Verify multiple movements sum correctly without double counting."""
        movements = [Decimal('50'), Decimal('30'), Decimal('-20')]
        expected_total = sum(movements)
        
        for qty in movements:
            InventoryService.record_movement(
                farm=self.farm,
                item=self.item,
                qty_delta=qty,
                ref_type='forensic_test',
                ref_id='FT-002'
            )
        
        final_qty = self._get_inventory_qty()
        self.assertEqual(
            final_qty,
            expected_total,
            f"Expected {expected_total}, got {final_qty}. Check for double counting."
        )
    
    def _get_inventory_qty(self) -> Decimal:
        inv = ItemInventory.objects.filter(farm=self.farm, item=self.item).first()
        return inv.qty if inv else Decimal('0')


class ForensicAuditCostingTests(TestCase):
    """
    HIGH-002: Verify that costing functions handle missing assets gracefully.
    """
    
    def test_get_machine_rate_returns_zero_for_none_asset(self):
        """
        Activities without machines should not raise exceptions.
        _get_machine_rate(None) should return Decimal(0).
        """
        result = _get_machine_rate(None)
        self.assertEqual(result, Decimal('0'))
    
    def test_get_machine_rate_returns_zero_for_zero_asset(self):
        """Edge case: asset_id=0 should also return 0."""
        result = _get_machine_rate(0)
        self.assertEqual(result, Decimal('0'))
