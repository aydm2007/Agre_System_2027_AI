from datetime import date, timedelta
from decimal import Decimal
import tempfile
import time
from unittest.mock import Mock, patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from kombu.exceptions import OperationalError as KombuOperationalError
from rest_framework.test import APIClient

from smart_agri.core.api.reporting import _generate_advanced_report_inline
from smart_agri.core.api.viewsets.farm import FarmViewSet
from smart_agri.core.models import Activity, ActivityItem, Crop, CropPlan, CropPlanBudgetLine, DailyLog, Farm, Task
from smart_agri.core.models.activity import ActivityLocation
from smart_agri.core.models.report import AsyncReportRequest
from smart_agri.core.services.reporting_orchestration_service import ReportingOrchestrationService
from smart_agri.inventory.models import Item, ItemInventory
from smart_agri.core.models.crop import CropRecipe, CropRecipeMaterial
from smart_agri.core.models.farm import Location
from smart_agri.core.models.planning import Season
from smart_agri.core.services.commercial_reporting_service import CommercialReportingService
from smart_agri.core.services.reporting_service import ArabicReportService
from rest_framework.test import APIRequestFactory


class PredictiveVarianceRuntimeTests(TestCase):
    def setUp(self):
        suffix = uuid4().hex[:8]
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username=f"variance-{suffix}",
            password="pass1234",
            is_superuser=True,
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name=f"Farm {suffix}", slug=f"farm-{suffix}", region="R1")
        self.crop = Crop.objects.create(name=f"Crop {suffix}", mode="Open")
        self.plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name=f"Plan {suffix}",
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() + timedelta(days=5),
            status="active",
        )
        CropPlanBudgetLine.objects.create(
            crop_plan=self.plan,
            category=CropPlanBudgetLine.CATEGORY_MATERIALS,
            total_budget=Decimal("100.0000"),
        )
        log = DailyLog.objects.create(farm=self.farm, log_date=date.today())
        item = Item.objects.create(name=f"Item {suffix}", group="General", uom="kg", unit_price=Decimal("10.000"))
        ItemInventory.objects.create(farm=self.farm, item=item, qty=Decimal("50.000"), uom="kg")
        activity = Activity.objects.create(log=log, crop=self.crop, crop_plan=self.plan, days_spent=Decimal("1"))
        ActivityItem.objects.create(activity=activity, item=item, qty=Decimal("2.000"), uom="kg")

    def test_predictive_variance_uses_crop_plan_without_location_field(self):
        response = self.client.get(f"/api/v1/predictive-variance/?farm={self.farm.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        payload = response.data["results"][0]
        self.assertEqual(payload["plan_id"], self.plan.id)
        self.assertEqual(Decimal(payload["actual_material_cost"]), Decimal("20.0000"))


class AdvancedReportFallbackTests(TestCase):
    def setUp(self):
        suffix = uuid4().hex[:8]
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username=f"report-{suffix}",
            password="pass1234",
            is_superuser=True,
            is_staff=True,
        )
        self.farm = Farm.objects.create(name=f"Farm {suffix}", slug=f"report-farm-{suffix}", region="R2")
        self.crop = Crop.objects.create(name=f"Report Crop {suffix}", mode="Open")
        self.task = Task.objects.create(crop=self.crop, stage="Care", name=f"Task {suffix}")
        self.location = Location.objects.create(farm=self.farm, name=f"Report Location {suffix}", type="Field")

    @patch("smart_agri.core.tasks.report_tasks.generate_advanced_report.delay")
    @patch("smart_agri.core.services.reporting_orchestration_service.ReportingOrchestrationService._fallback_inline")
    def test_enqueue_or_fallback_handles_kombu_broker_failure(self, mock_fallback_inline, mock_delay):
        mock_delay.side_effect = KombuOperationalError("broker unavailable")
        inline_generator = Mock()
        job = AsyncReportRequest.objects.create(
            created_by=self.user,
            report_type=AsyncReportRequest.REPORT_ADVANCED,
            params={"farm_id": self.farm.id},
        )

        ReportingOrchestrationService.enqueue_or_fallback(
            actor=self.user,
            job=job,
            params={"farm_id": self.farm.id},
            inline_generator=inline_generator,
        )

        deadline = time.time() + 2
        while time.time() < deadline and mock_fallback_inline.call_count == 0:
            time.sleep(0.05)

        mock_fallback_inline.assert_called_once()
        call_kwargs = mock_fallback_inline.call_args.kwargs
        self.assertEqual(call_kwargs["actor"], self.user)
        self.assertEqual(call_kwargs["job"], job)
        self.assertEqual(call_kwargs["params"]["farm_id"], self.farm.id)
        self.assertEqual(call_kwargs["inline_generator"], inline_generator)
        self.assertIn("broker unavailable", call_kwargs["reason"])

    def test_inline_generator_completes_when_broker_is_unavailable(self):
        plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name="Inline Plan",
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
            area=Decimal("2.0000"),
        )
        log = DailyLog.objects.create(farm=self.farm, log_date=date.today())
        activity = Activity.objects.create(
            log=log,
            crop=self.crop,
            crop_plan=plan,
            task=self.task,
            days_spent=Decimal("1"),
        )
        ActivityLocation.objects.create(activity=activity, location=self.location)
        job = AsyncReportRequest.objects.create(
            created_by=self.user,
            report_type=AsyncReportRequest.REPORT_ADVANCED,
            params={
                "farm_id": str(self.farm.id),
                "crop_id": str(self.crop.id),
                "task_id": str(self.task.id),
                "location_id": str(self.location.id),
                "include_details": "true",
            },
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir):
                _generate_advanced_report_inline(job)

        job.refresh_from_db()
        self.assertEqual(job.status, AsyncReportRequest.STATUS_COMPLETED)
        self.assertTrue(str(job.result_url or "").endswith(f"advanced-report-{job.id}.json"))


class ReportingContractsRuntimeTests(TestCase):
    def setUp(self):
        suffix = uuid4().hex[:8]
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username=f"contracts-{suffix}",
            password="pass1234",
            is_superuser=True,
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name=f"Farm {suffix}", slug=f"contracts-farm-{suffix}", region="R3")
        self.crop = Crop.objects.create(name=f"Crop {suffix}", mode="Open")
        self.task = Task.objects.create(crop=self.crop, stage="Preparation", name=f"Task {suffix}")
        self.location = Location.objects.create(farm=self.farm, name=f"Location {suffix}", type="Field")
        self.season_a = Season.objects.create(name=f"S1-{suffix}", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30))
        self.season_b = Season.objects.create(name=f"S2-{suffix}", start_date=date(2026, 3, 1), end_date=date(2026, 12, 31))

    def test_advanced_report_accepts_farm_id_and_season_id_filters(self):
        plan_a = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name="Plan A",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            area=Decimal("5.0000"),
            season=self.season_a,
        )
        plan_b = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name="Plan B",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            area=Decimal("5.0000"),
            season=self.season_b,
        )
        today = date.today()
        log_a = DailyLog.objects.create(farm=self.farm, log_date=today - timedelta(days=2))
        log_b = DailyLog.objects.create(farm=self.farm, log_date=today - timedelta(days=1))
        activity_a = Activity.objects.create(
            log=log_a,
            crop=self.crop,
            crop_plan=plan_a,
            task=self.task,
            days_spent=Decimal("1"),
        )
        activity_b = Activity.objects.create(
            log=log_b,
            crop=self.crop,
            crop_plan=plan_b,
            task=self.task,
            days_spent=Decimal("1"),
        )
        ActivityLocation.objects.create(activity=activity_a, location=self.location)
        ActivityLocation.objects.create(activity=activity_b, location=self.location)

        response = self.client.get(
            "/api/v1/advanced-report/",
            {
                "farm_id": self.farm.id,
                "season_id": self.season_a.id,
                "crop_id": self.crop.id,
                "task_id": self.task.id,
                "location_id": self.location.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["details_meta"]["total"], 1)
        self.assertEqual(response.data["summary"]["filters"]["crop_id"], self.crop.id)
        self.assertEqual(response.data["summary"]["filters"]["task_id"], self.task.id)
        self.assertEqual(response.data["summary"]["filters"]["location_id"], self.location.id)
        self.assertEqual(response.data["summary"]["filters"]["season_id"], self.season_a.id)

    def test_financial_risk_zone_returns_results_without_runtime_failure(self):
        item = Item.objects.create(name="Fertilizer", group="General", uom="kg", unit_price=Decimal("10.0000"))
        ItemInventory.objects.create(farm=self.farm, item=item, qty=Decimal("50.000"), uom="kg")
        recipe = CropRecipe.objects.create(crop=self.crop, name="Standard Recipe")
        CropRecipeMaterial.objects.create(
            recipe=recipe,
            item=item,
            standard_qty_per_ha=Decimal("2.000"),
        )
        plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            recipe=recipe,
            name="Risk Plan",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            area=Decimal("5.0000"),
            season=self.season_a,
        )
        log = DailyLog.objects.create(farm=self.farm, log_date=date(2026, 2, 10))
        activity = Activity.objects.create(log=log, crop=self.crop, crop_plan=plan, days_spent=Decimal("1"))
        ActivityItem.objects.create(
            activity=activity,
            item=item,
            qty=Decimal("5.000"),
            total_cost=Decimal("150.0000"),
            uom="kg",
        )

        response = self.client.get(
            "/api/v1/crop-plans/financial-risk-zone/",
            {"farm_id": self.farm.id, "crop_id": self.crop.id, "season_id": self.season_a.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["crop_plan_id"], plan.id)

    def test_profitability_pdf_accepts_start_date_fallback(self):
        service = ArabicReportService()

        with patch("smart_agri.finance.models.FinancialLedger.objects.filter") as mock_filter:
            qs = mock_filter.return_value
            filtered_qs = qs.filter.return_value
            filtered_qs.values.return_value.annotate.return_value.order_by.return_value = []

            service.generate_profitability_pdf(
                {"farm_id": self.farm.id, "start_date": "2026-01-01", "end_date": "2026-01-31"}
            )

            self.assertTrue(qs.filter.called)

    def test_commercial_snapshot_accepts_start_date_fallback(self):
        snapshot = CommercialReportingService.build_snapshot(
            {
                "farm_id": self.farm.id,
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
            }
        )

        self.assertEqual(snapshot["filters"]["start"], "2026-01-01")
        self.assertEqual(snapshot["filters"]["end"], "2026-01-31")


class FarmPaginationOrderingTests(TestCase):
    def test_farm_viewset_queryset_is_ordered_before_pagination(self):
        suffix = uuid4().hex[:8]
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username=f"farm-order-{suffix}",
            password="pass1234",
            is_superuser=True,
            is_staff=True,
        )
        Farm.objects.create(name=f"Beta {suffix}", slug=f"beta-{suffix}", region="R1")
        Farm.objects.create(name=f"Alpha {suffix}", slug=f"alpha-{suffix}", region="R1")

        factory = APIRequestFactory()
        request = factory.get("/api/v1/farms/")
        request.user = user

        view = FarmViewSet()
        view.request = request
        queryset = view.get_queryset()

        self.assertTrue(queryset.ordered)
        self.assertEqual(
            list(queryset.values_list("name", flat=True)[:2]),
            sorted(list(queryset.values_list("name", flat=True)[:2])),
        )
