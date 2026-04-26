from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from smart_agri.core.models import (
    Activity,
    ActivityCostSnapshot,
    ActivityItem,
    ActivityMachineUsage,
    Asset,
    CostConfiguration,
    Crop,
    CropPlan,
    DailyLog,
    Farm,
    FarmSettings,
    Item,
    ItemInventory,
    LaborRate,
    Location,
    MachineRate,
)
from smart_agri.core.services.costing import calculate_activity_cost
from smart_agri.finance.models import CostCenter, FinancialLedger, FiscalPeriod, FiscalYear
from smart_agri.finance.services.core_finance import FinanceService

User = get_user_model()


class AlJarubaSimpleModeSimulation(TestCase):
    """
    SIMPLE-mode simulation for Al-Jaruba.

    Covers:
      1. Seasonal and perennial crop plans on the current CropPlan contract.
      2. Technical cost calculation using the canonical service layer.
      3. Shadow-ledger synchronization without reopening governed ERP authoring.
    """

    def setUp(self):
        self.field_op = User.objects.create_user(username="jaruba_op", password="password")

        self.farm = Farm.objects.create(name="الجروبة", slug="al-jaruba", tier="MEDIUM")
        FarmSettings.objects.create(farm=self.farm, mode=FarmSettings.MODE_SIMPLE)

        CostConfiguration.objects.create(
            farm=self.farm,
            overhead_rate_per_hectare=Decimal("50.00"),
            currency="YER",
        )
        LaborRate.objects.create(
            farm=self.farm,
            role_name="عامل يومي",
            daily_rate=Decimal("3000.00"),
            cost_per_hour=Decimal("3000.00"),
        )

        today = timezone.localdate()
        fiscal_year = FiscalYear.objects.create(
            farm=self.farm,
            year=today.year,
            start_date=today.replace(month=1, day=1),
            end_date=today.replace(month=12, day=31),
        )
        FiscalPeriod.objects.create(
            fiscal_year=fiscal_year,
            month=today.month,
            start_date=today.replace(day=1),
            end_date=today.replace(day=28),
            status=FiscalPeriod.STATUS_OPEN,
            is_closed=False,
        )

        self.locations = {
            "seasonal": Location.objects.create(farm=self.farm, name="حقل الطماطم", code="JAR-TOM"),
            "mango": Location.objects.create(farm=self.farm, name="بستان المانجو", code="JAR-MAN"),
        }

        self.tractor = Asset.objects.create(
            farm=self.farm,
            category="Machinery",
            code="TRACTOR-01",
            name="جرار الجروبة",
            asset_type="tractor",
            purchase_value=Decimal("20000.00"),
            operational_cost_per_hour=Decimal("150.00"),
        )
        self.well = Asset.objects.create(
            farm=self.farm,
            category="Well",
            code="WELL-01",
            name="بئر الجروبة",
            asset_type="well",
            purchase_value=Decimal("50000.00"),
            operational_cost_per_hour=Decimal("150.00"),
        )
        MachineRate.objects.create(
            asset=self.tractor,
            daily_rate=Decimal("150.00"),
            cost_per_hour=Decimal("150.00"),
        )
        MachineRate.objects.create(
            asset=self.well,
            daily_rate=Decimal("150.00"),
            cost_per_hour=Decimal("150.00"),
        )

        self.urea = Item.objects.create(
            name="سماد يوريا",
            group="Fertilizer",
            uom="kg",
            unit_price=Decimal("500.00"),
        )
        ItemInventory.objects.create(
            farm=self.farm,
            location=self.locations["seasonal"],
            item=self.urea,
            qty=Decimal("100.000"),
            uom="kg",
        )

        self.seasonal_crop = Crop.objects.create(name="طماطم", is_perennial=False)
        self.perennial_crop = Crop.objects.create(name="مانجو", is_perennial=True)

        self.seasonal_plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.seasonal_crop,
            name="خطة الطماطم 2026",
            start_date=today,
            end_date=today + timedelta(days=120),
            area=Decimal("10.00"),
            status="ACTIVE",
        )
        self.perennial_plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.perennial_crop,
            name="خطة المانجو 2026",
            start_date=today,
            end_date=today + timedelta(days=180),
            area=Decimal("5.00"),
            status="ACTIVE",
        )

        self.cost_center_s = CostCenter.objects.create(farm=self.farm, code="CC-TOM-01", name="طماطم")
        self.cost_center_p = CostCenter.objects.create(farm=self.farm, code="CC-MAN-01", name="مانجو")

    def _sync_shadow_costing(self, activity, *, cost_center):
        calculate_activity_cost(activity)
        activity.refresh_from_db()
        activity.cost_center = cost_center
        FinanceService.sync_activity_ledger(activity, self.field_op)
        return ActivityCostSnapshot.objects.get(activity=activity)

    def test_al_jaruba_simple_comprehensive_cycle(self):
        self.assertEqual(FinancialLedger.objects.filter(farm=self.farm).count(), 0)

        seasonal_log = DailyLog.objects.create(
            farm=self.farm,
            log_date=timezone.localdate(),
            created_by=self.field_op,
            notes="حراثة وتسميد حقل الطماطم",
        )
        seasonal_activity = Activity.objects.create(
            log=seasonal_log,
            crop_plan=self.seasonal_plan,
            crop=self.seasonal_crop,
            created_by=self.field_op,
            location=self.locations["seasonal"],
            asset=self.tractor,
            days_spent=Decimal("3.00"),
            planted_area=Decimal("10000"),
            planted_uom="m2",
        )
        ActivityMachineUsage.objects.create(activity=seasonal_activity, machine_hours=Decimal("4.00"))
        ActivityItem.objects.create(activity=seasonal_activity, item=self.urea, qty=Decimal("50.00"), uom="kg")

        seasonal_snapshot = self._sync_shadow_costing(seasonal_activity, cost_center=self.cost_center_s)

        self.assertEqual(seasonal_snapshot.cost_materials, Decimal("25000.0000"))
        self.assertEqual(seasonal_snapshot.cost_labor, Decimal("9000.0000"))
        self.assertEqual(seasonal_snapshot.cost_machinery, Decimal("600.0000"))
        self.assertEqual(seasonal_snapshot.cost_overhead, Decimal("50.0000"))
        self.assertEqual(seasonal_snapshot.cost_total, Decimal("34650.00"))

        seasonal_ledger = FinancialLedger.objects.filter(activity=seasonal_activity, farm=self.farm)
        self.assertEqual(seasonal_ledger.count(), 8)
        self.assertEqual(
            seasonal_ledger.aggregate(total_debit=models.Sum("debit"))["total_debit"],
            seasonal_ledger.aggregate(total_credit=models.Sum("credit"))["total_credit"],
        )

        perennial_log = DailyLog.objects.create(
            farm=self.farm,
            log_date=timezone.localdate(),
            created_by=self.field_op,
            notes="ري وخدمة بستان المانجو",
        )
        perennial_activity = Activity.objects.create(
            log=perennial_log,
            crop_plan=self.perennial_plan,
            crop=self.perennial_crop,
            created_by=self.field_op,
            location=self.locations["mango"],
            asset=self.well,
            days_spent=Decimal("2.00"),
            planted_area=Decimal("5000"),
            planted_uom="m2",
        )
        ActivityMachineUsage.objects.create(activity=perennial_activity, machine_hours=Decimal("8.00"))

        perennial_snapshot = self._sync_shadow_costing(perennial_activity, cost_center=self.cost_center_p)

        self.assertEqual(perennial_snapshot.cost_materials, Decimal("0.0000"))
        self.assertEqual(perennial_snapshot.cost_labor, Decimal("6000.0000"))
        self.assertEqual(perennial_snapshot.cost_machinery, Decimal("1200.0000"))
        self.assertEqual(perennial_snapshot.cost_overhead, Decimal("25.0000"))
        self.assertEqual(perennial_snapshot.cost_total, Decimal("7225.00"))

        perennial_ledger = FinancialLedger.objects.filter(activity=perennial_activity, farm=self.farm)
        self.assertEqual(perennial_ledger.count(), 6)
        self.assertEqual(
            perennial_ledger.aggregate(total_debit=models.Sum("debit"))["total_debit"],
            perennial_ledger.aggregate(total_credit=models.Sum("credit"))["total_credit"],
        )

        self.assertEqual(seasonal_log.status, DailyLog.STATUS_DRAFT)
        self.assertEqual(perennial_log.status, DailyLog.STATUS_DRAFT)
        self.assertEqual(self.farm.settings.mode, FarmSettings.MODE_SIMPLE)
