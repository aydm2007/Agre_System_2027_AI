"""
[AGRI-GUARDIAN] Axis 8 Compliance: Variance + Activity Creation Integration Test
Tests compute_log_variance with real cost data (unmocked) to verify
WARNING/CRITICAL thresholds trigger correctly when activity costs
exceed crop plan budgets.
"""
from decimal import Decimal
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from smart_agri.core.models import (
    Activity, DailyLog, Farm,
)
from smart_agri.core.models.planning import CropPlan, Season, CropPlanLocation
from smart_agri.core.models.crop import Crop
from smart_agri.core.models.farm import Location
from smart_agri.core.services.variance import compute_log_variance
from smart_agri.finance.models import CostConfiguration


class VarianceActivityIntegrationTests(TestCase):
    """Integration test: activity costs → compute_log_variance (no mocks)."""

    def setUp(self):
        self.user = User.objects.create_user(username="var_test_user")
        self.farm = Farm.objects.create(
            name="Variance Test Farm",
            slug="variance-test-farm",
            region="Sanaa",
            area=Decimal("50.00"),
        )
        self.location = Location.objects.create(
            farm=self.farm,
            name="Variance Test Plot",
            type="Field",
        )
        # Set warning=10%, critical=20%
        CostConfiguration.objects.create(
            farm=self.farm,
            variance_warning_pct=Decimal("10.00"),
            variance_critical_pct=Decimal("20.00"),
        )
        self.season = Season.objects.create(
            name="Test Season 2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.crop = Crop.objects.create(name="Test Wheat")
        self.plan = CropPlan.objects.create(
            farm=self.farm,
            season=self.season,
            crop=self.crop,
            name="Variance Test Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            budget_total=Decimal("1000.00"),
            budget_materials=Decimal("1000.00")
        )
        CropPlanLocation.objects.create(crop_plan=self.plan, location=self.location, assigned_area=Decimal('10.0'))
        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date=date(2026, 3, 1),
            created_by=self.user,
            status=DailyLog.STATUS_SUBMITTED,
        )

    def test_ok_within_threshold(self):
        """Activity cost within 10% of budget → OK."""
        Activity.objects.create(
            log=self.log,
            crop_plan=self.plan,
            days_spent=Decimal("1.00"),
            cost_total=Decimal("1050.00"),   # +5% over budget
            created_by=self.user,
        )
        result = compute_log_variance(self.log)
        self.assertEqual(result["status"], "OK")

    def test_warning_threshold_triggered(self):
        """Activity cost 15% over budget → WARNING."""
        Activity.objects.create(
            log=self.log,
            crop_plan=self.plan,
            days_spent=Decimal("1.00"),
            cost_total=Decimal("1150.00"),   # +15% over budget
            created_by=self.user,
        )
        result = compute_log_variance(self.log)
        self.assertEqual(result["status"], "WARNING")
        self.assertGreaterEqual(result["max_deviation_pct"], Decimal("10.00"))

    def test_critical_threshold_triggered(self):
        """Activity cost 25% over budget → CRITICAL."""
        Activity.objects.create(
            log=self.log,
            crop_plan=self.plan,
            days_spent=Decimal("1.00"),
            cost_total=Decimal("1250.00"),   # +25% over budget
            created_by=self.user,
        )
        result = compute_log_variance(self.log)
        self.assertEqual(result["status"], "CRITICAL")
        self.assertGreaterEqual(result["max_deviation_pct"], Decimal("20.00"))

    def test_zero_budget_triggers_deviation(self):
        """Activity cost > 0 with zero budget → 100% deviation."""
        self.plan.budget_total = Decimal("0.00")
        self.plan.save()
        Activity.objects.create(
            log=self.log,
            crop_plan=self.plan,
            days_spent=Decimal("1.00"),
            cost_total=Decimal("500.00"),
            created_by=self.user,
        )
        result = compute_log_variance(self.log)
        self.assertEqual(result["max_deviation_pct"], Decimal("100.00"))

    def test_no_activities_returns_ok(self):
        """Empty log returns OK with zero deviation."""
        result = compute_log_variance(self.log)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["max_deviation_pct"], Decimal("0.00"))
