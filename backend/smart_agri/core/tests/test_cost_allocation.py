from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from smart_agri.core.models import (
    Farm, Location, Crop, Task, CropPlan, Activity, 
    DailyLog,
)
from smart_agri.finance.models import CostConfiguration, FinancialLedger, ActualExpense
from smart_agri.core.services.cost_allocation import CostAllocationService

class CostAllocationServiceTest(TestCase):
    
    def setUp(self):
        # Basic Setup
        self.farm = Farm.objects.create(name="Allocation Farm", slug="alloc-farm", region="Test")
        self.location = Location.objects.create(farm=self.farm, name="Field 1", type="Field")
        self.crop = Crop.objects.create(name="Wheat", mode="Open")
        self.task_planting = Task.objects.create(name="Sowing", crop=self.crop, stage="Planting", requires_area=True)
        self.task_care = Task.objects.create(name="Watering", crop=self.crop, stage="Care")
        
        # Valid Dates
        self.p_start = timezone.now().date().replace(month=1, day=1)
        self.p_end = self.p_start.replace(month=6, day=30)
        
        # Crop Plan
        self.plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            location=self.location,
            name="Winter 2026",
            start_date=self.p_start,
            end_date=self.p_end,
        )
        
        # Log & Activities (to define area)
        self.log = DailyLog.objects.create(farm=self.farm, log_date=self.p_start)
        
        # Planting Activity (10 hectares = 100,000 m2)
        Activity.objects.create(
            log=self.log,
            crop=self.crop,
            task=self.task_planting,
            location=self.location,
            crop_plan=self.plan,
            planted_area=Decimal("100000"), # 10 ha
            planted_uom="m2"
        )

    def test_allocate_overheads_by_area(self):
        # 1. Config
        CostConfiguration.objects.create(
            farm=self.farm,
            overhead_rate_per_hectare=Decimal("500.00"), # 500 per ha
            currency="SAR"
        )
        
        # 2. Run Allocation
        total = CostAllocationService.allocate_overheads_by_area(
            self.farm, self.p_start, self.p_end
        )
        
        # 3. Assert Total
        # Area = 10 ha. Rate = 500. Total = 5000.
        self.assertEqual(total, Decimal("5000.00"))
        
        # 4. [AGRI-GUARDIAN] Assert Double-Entry: Debit Overhead
        debit_entries = FinancialLedger.objects.filter(
            crop_plan=self.plan, 
            account_code=FinancialLedger.ACCOUNT_OVERHEAD
        )
        self.assertEqual(debit_entries.count(), 1)
        self.assertEqual(debit_entries.first().debit, Decimal("5000.00"))

        # 5. [AGRI-GUARDIAN] Assert Double-Entry: Credit Sector Payable
        credit_entries = FinancialLedger.objects.filter(
            crop_plan=self.plan,
            account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE
        )
        self.assertEqual(credit_entries.count(), 1)
        self.assertEqual(credit_entries.first().credit, Decimal("5000.00"))

        # 6. [AGRI-GUARDIAN] Verify balanced: Sum(Debit) == Sum(Credit)
        total_debit = debit_entries.first().debit
        total_credit = credit_entries.first().credit
        self.assertEqual(total_debit, total_credit, "Double-entry must balance")

    def test_allocate_actual_bills(self):
        # 1. Create Expense
        expense = ActualExpense.objects.create(
            farm=self.farm,
            amount=Decimal("1000.00"),
            description="Electricity Bill",
            account_code="EXP-ELEC",
            date=self.p_start,
            period_start=self.p_start,
            period_end=self.p_start # Within range
        )
        
        # 2. Add another plan to test distribution
        location2 = Location.objects.create(farm=self.farm, name="Field 2", type="Field")
        plan2 = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            location=location2,
            name="Late Winter",
            start_date=self.p_start,
            end_date=self.p_end,
        )
        # Plan 2 has 10 ha as well
        Activity.objects.create(
            log=self.log,
            crop=self.crop,
            task=self.task_planting,
            location=self.location,
            crop_plan=plan2,
            planted_area=Decimal("100000"), # 10 ha
            planted_uom="m2"
        )
        
        # 3. Run Allocation
        distributed = CostAllocationService.allocate_actual_bills(
            self.farm, self.p_start, self.p_end
        )
        
        # 4. Assert
        # Total Area = 20 ha. Expense = 1000. Each plan gets 500.
        self.assertEqual(distributed, Decimal("1000.00"))
        
        self.assertEqual(
            FinancialLedger.objects.filter(crop_plan=self.plan, account_code="EXP-ELEC").first().debit,
            Decimal("500.00")
        )
        self.assertEqual(
            FinancialLedger.objects.filter(crop_plan=plan2, account_code="EXP-ELEC").first().debit,
            Decimal("500.00")
        )
        
        expense.refresh_from_db()
        self.assertTrue(expense.is_allocated)
