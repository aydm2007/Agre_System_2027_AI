"""
اختبارات التحقق من الإصلاحات الجديدة - المرحلة 5.

FORENSIC AUDIT REMEDIATION (2026-01-24): Testing Phase
- Tests for strict costing mode
- Tests for unified inventory service
- Tests for refactored tree services
"""
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model

from smart_agri.core.models import (
    Farm, Item, Unit, ItemInventory, StockMovement,
    Crop, Task, DailyLog, Activity, Location,
    LaborRate, MachineRate, Asset, CostConfiguration,
)
from smart_agri.core.services.costing import (
    _get_labor_rate, _get_machine_rate, _get_overhead_rate,
    COSTING_STRICT_MODE
)
from smart_agri.core.services.inventory_service import InventoryService


User = get_user_model()


class StrictCostingModeTests(TestCase):
    """
    اختبارات وضع التكاليف الصارم.
    
    يتحقق من أن الدوال ترفع استثناءات عند غياب الإعدادات.
    """
    
    def setUp(self):
        self.farm = Farm.objects.create(name='Strict Test Farm', slug='strict-test', region='A')
    
    def test_labor_rate_raises_on_missing_in_strict_mode(self):
        """يجب أن يرفع استثناء عند عدم وجود معدل عمالة في الوضع الصارم."""
        with self.assertRaises(ValueError) as ctx:
            _get_labor_rate(self.farm.id, strict=True)
        
        self.assertIn("معدل عمالة", str(ctx.exception))
        self.assertIn(str(self.farm.id), str(ctx.exception))
    
    def test_labor_rate_returns_zero_in_non_strict_mode(self):
        """يجب أن يرجع صفر بدون استثناء في الوضع غير الصارم."""
        result = _get_labor_rate(self.farm.id, strict=False)
        self.assertEqual(result, Decimal("0"))
    
    def test_labor_rate_success_with_config(self):
        """يجب أن يرجع القيمة الصحيحة عند وجود الإعدادات."""
        from django.utils import timezone
        LaborRate.objects.create(
            farm=self.farm, 
            role_name='Worker',
            cost_per_hour=Decimal('500.00'),
            effective_date=timezone.now().date()
        )
        
        result = _get_labor_rate(self.farm.id, strict=True)
        self.assertEqual(result, Decimal('500.00'))
    
    def test_overhead_rate_raises_on_missing_in_strict_mode(self):
        """يجب أن يرفع استثناء عند عدم وجود إعدادات التكلفة."""
        with self.assertRaises(ValueError) as ctx:
            _get_overhead_rate(self.farm.id, strict=True)
        
        self.assertIn("CostConfiguration", str(ctx.exception))
    
    def test_overhead_rate_success_with_config(self):
        """يجب أن يرجع القيمة الصحيحة عند وجود الإعدادات."""
        CostConfiguration.objects.create(
            farm=self.farm,
            overhead_rate_per_hectare=Decimal('100.00'),
            currency='SAR'
        )
        
        result = _get_overhead_rate(self.farm.id, strict=True)
        self.assertEqual(result, Decimal('100.00'))
    
    def test_machine_rate_returns_zero_for_none_asset(self):
        """النشاط بدون آلة لا يجب أن يرفع استثناء."""
        result = _get_machine_rate(None, strict=True)
        self.assertEqual(result, Decimal('0'))
    
    def test_machine_rate_raises_for_missing_asset_rate(self):
        """يجب أن يرفع استثناء عند تحديد آلة بدون معدل."""
        asset = Asset.objects.create(
            farm=self.farm,
            name='Tractor',
            category='Machinery'
        )
        
        with self.assertRaises(ValueError) as ctx:
            _get_machine_rate(asset.id, strict=True)
        
        self.assertIn("معدل آلة", str(ctx.exception))


class UnifiedInventoryServiceTests(TransactionTestCase):
    """
    اختبارات خدمة المخزون الموحدة.
    
    يتحقق من أن Python هو المصدر الوحيد للحقيقة.
    """
    
    def setUp(self):
        self.farm = Farm.objects.create(name='Inventory Test', slug='inv-test', region='A')
        self.location = Location.objects.create(farm=self.farm, name='Block A')
        self.unit = Unit.objects.create(code='kg_inv', name='Kilogram', symbol='kg', category='mass')
        self.item = Item.objects.create(
            name='Test Item',
            group='Test',
            uom='kg',
            unit=self.unit,
        )
    
    def test_record_movement_creates_inventory(self):
        """يجب أن تنشئ حركة جديدة سجل مخزون."""
        movement = InventoryService.record_movement(
            farm=self.farm,
            item=self.item,
            qty_delta=Decimal('100.00'),
            location=self.location,
            ref_type='test',
            ref_id='T-001',
        )
        
        self.assertIsNotNone(movement)
        
        inventory = ItemInventory.objects.get(
            farm=self.farm,
            item=self.item,
            location=self.location
        )
        self.assertEqual(inventory.qty, Decimal('100.00'))
    
    def test_multiple_movements_accumulate(self):
        """يجب أن تجمع الحركات المتعددة بشكل صحيح."""
        InventoryService.record_movement(
            farm=self.farm, item=self.item, qty_delta=Decimal('50'),
            ref_type='test', ref_id='T-001'
        )
        InventoryService.record_movement(
            farm=self.farm, item=self.item, qty_delta=Decimal('30'),
            ref_type='test', ref_id='T-002'
        )
        InventoryService.record_movement(
            farm=self.farm, item=self.item, qty_delta=Decimal('-20'),
            ref_type='test', ref_id='T-003'
        )
        
        inventory = ItemInventory.objects.get(farm=self.farm, item=self.item, location__isnull=True)
        self.assertEqual(inventory.qty, Decimal('60'))
    
    def test_negative_inventory_rejected(self):
        """يجب رفض الحركات التي تؤدي لمخزون سالب."""
        # أولاً: إنشاء رصيد
        InventoryService.record_movement(
            farm=self.farm, item=self.item, qty_delta=Decimal('10'),
            ref_type='test', ref_id='T-001'
        )
        
        # ثانياً: محاولة سحب أكثر من المتاح
        with self.assertRaises(ValueError) as ctx:
            InventoryService.record_movement(
                farm=self.farm, item=self.item, qty_delta=Decimal('-50'),
                ref_type='test', ref_id='T-002'
            )
        
        self.assertIn("سالب", str(ctx.exception))
    
    def test_negative_from_zero_rejected(self):
        """يجب رفض السحب من مخزون غير موجود."""
        with self.assertRaises(ValueError) as ctx:
            InventoryService.record_movement(
                farm=self.farm, item=self.item, qty_delta=Decimal('-10'),
                ref_type='test', ref_id='T-001'
            )
        
        self.assertIn("غير موجود", str(ctx.exception))
