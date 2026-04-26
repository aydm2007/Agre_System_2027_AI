"""
Tests for Phase 5 services: OverheadAllocationService, VarianceAnalysisService.

AGENTS.md Coverage:
  - Axis 2: Idempotency (overhead alloc duplicate guard)
  - Axis 4: Fund Accounting (double-entry)
  - Axis 5: Decimal precision
  - Axis 6: Farm-scoped
  - Axis 8: Variance controls
"""

from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()


class OverheadAllocationTest(TestCase):
    """Tests for OverheadAllocationService."""

    @classmethod
    def setUpTestData(cls):
        from smart_agri.core.models.farm import Farm, Location
        from smart_agri.core.models.crop import Crop
        from smart_agri.core.models.planning import CropPlan, Season
        cls.user = User.objects.create_user(username='alloc_actor', password='pass123')
        cls.farm = Farm.objects.create(name="مزرعة التوزيع", slug="overhead-alloc-farm")
        cls.season = Season.objects.create(
            name="2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        )
        cls.crop_wheat = Crop.objects.create(name="قمح", farm=cls.farm)
        cls.crop_tomato = Crop.objects.create(name="طماطم", farm=cls.farm)
        loc1 = Location.objects.create(farm=cls.farm, name="حقل أ", area_hectares=Decimal("70"))
        loc2 = Location.objects.create(farm=cls.farm, name="حقل ب", area_hectares=Decimal("30"))
        cls.plan_wheat = CropPlan.objects.create(
            farm=cls.farm, crop=cls.crop_wheat, location=loc1,
            name="خطة القمح", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
            area=Decimal("70.00"), season=cls.season,
        )
        cls.plan_tomato = CropPlan.objects.create(
            farm=cls.farm, crop=cls.crop_tomato, location=loc2,
            name="خطة الطماطم", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
            area=Decimal("30.00"), season=cls.season,
        )

    def _add_overhead(self, amount):
        """Helper: create overhead debit entry."""
        from smart_agri.finance.models import FinancialLedger
        FinancialLedger.objects.create(
            farm=self.farm,
            account_code=FinancialLedger.ACCOUNT_OVERHEAD,
            debit=amount, credit=Decimal("0.0000"),
            description="فاتورة كهرباء",
        )

    def test_allocate_by_area(self):
        """[Axis 4/5] Allocates overhead proportionally: 70% wheat, 30% tomato."""
        from smart_agri.core.services.overhead_allocation_service import OverheadAllocationService
        self._add_overhead(Decimal("10000.0000"))

        result = OverheadAllocationService.allocate_monthly_overhead(
            farm_id=self.farm.id, year=2026, month=3, actor=self.user,
        )
        self.assertEqual(result['status'], 'allocated')
        self.assertEqual(result['total_overhead'], '10000.0000')
        self.assertEqual(len(result['allocations']), 2)

        wheat_alloc = result['allocations'][0]
        tomato_alloc = result['allocations'][1]
        self.assertEqual(wheat_alloc['amount'], '7000.0000')
        self.assertEqual(tomato_alloc['amount'], '3000.0000')

    def test_idempotent(self):
        """[Axis 2] Second allocation for same period is idempotent."""
        from smart_agri.core.services.overhead_allocation_service import OverheadAllocationService
        self._add_overhead(Decimal("5000.0000"))

        r1 = OverheadAllocationService.allocate_monthly_overhead(
            farm_id=self.farm.id, year=2026, month=4, actor=self.user,
        )
        self.assertEqual(r1['status'], 'allocated')

        r2 = OverheadAllocationService.allocate_monthly_overhead(
            farm_id=self.farm.id, year=2026, month=4, actor=self.user,
        )
        self.assertEqual(r2['status'], 'already_allocated')

    def test_no_overhead(self):
        """Returns 'no_overhead' when nothing to allocate."""
        from smart_agri.core.services.overhead_allocation_service import OverheadAllocationService
        result = OverheadAllocationService.allocate_monthly_overhead(
            farm_id=self.farm.id, year=2026, month=5, actor=self.user,
        )
        self.assertEqual(result['status'], 'no_overhead')

    def test_requires_farm_id(self):
        """[Axis 6] Raises ValidationError without farm_id."""
        from smart_agri.core.services.overhead_allocation_service import OverheadAllocationService
        with self.assertRaises(ValidationError):
            OverheadAllocationService.allocate_monthly_overhead(
                farm_id=None, year=2026, month=3, actor=self.user,
            )


class VarianceAnalysisTest(TestCase):
    """Tests for VarianceAnalysisService."""

    @classmethod
    def setUpTestData(cls):
        from smart_agri.core.models.farm import Farm
        from smart_agri.core.models.crop import Crop
        from smart_agri.core.models.planning import Season
        cls.farm = Farm.objects.create(name="مزرعة الانحراف", slug="variance-test-farm")
        cls.season = Season.objects.create(
            name="2026-VA", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        )
        cls.crop = Crop.objects.create(name="طماطم", farm=cls.farm)

    def test_empty_report(self):
        """Returns empty plans list when no crop plans match."""
        from smart_agri.core.services.variance_analysis_service import VarianceAnalysisService
        result = VarianceAnalysisService.get_variance_report(farm_id=self.farm.id)
        self.assertEqual(result['plans_count'], 0)

    def test_requires_farm_id(self):
        """[Axis 6] Returns error when farm_id is missing."""
        from smart_agri.core.services.variance_analysis_service import VarianceAnalysisService
        result = VarianceAnalysisService.get_variance_report(farm_id=None)
        self.assertIn('error', result)
