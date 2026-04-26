from datetime import date
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from smart_agri.core.models import Crop, DailyLog, Farm, Location
from smart_agri.core.models.inventory import BiologicalAssetCohort, TreeCensusVarianceAlert
from smart_agri.core.models.report import AsyncReportRequest
from smart_agri.accounts.models import FarmMembership
from smart_agri.inventory.models import Item, StockMovement


class ServiceLayerContractsTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username=f"svc-{uuid4().hex[:8]}",
            password="pass1234",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

        suffix = uuid4().hex[:8]
        self.farm = Farm.objects.create(name=f"Farm {suffix}", slug=f"farm-{suffix}", region="R1")
        self.location = Location.objects.create(farm=self.farm, name=f"Loc {suffix}")
        self.item = Item.objects.create(name=f"Item {suffix}", group="General", uom="kg")

    def test_qr_execute_requires_idempotency_header(self):
        response = self.client.post(
            "/api/v1/qr-operations/execute/",
            {
                "qr_string": f"ITEM:{self.item.id}",
                "action": "add",
                "farm_id": self.farm.id,
                "location_id": self.location.id,
                "amount": "1.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("X-Idempotency-Key", str(response.data))

    def test_qr_execute_idempotent_replay_no_double_write(self):
        payload = {
            "qr_string": f"ITEM:{self.item.id}",
            "action": "add",
            "farm_id": self.farm.id,
            "location_id": self.location.id,
            "amount": "2.00",
            "note": "idempotent test",
        }
        headers = {"HTTP_X_IDEMPOTENCY_KEY": f"qr-{uuid4().hex}"}

        first = self.client.post("/api/v1/qr-operations/execute/", payload, format="json", **headers)
        second = self.client.post("/api/v1/qr-operations/execute/", payload, format="json", **headers)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.data, second.data)
        self.assertEqual(
            StockMovement.objects.filter(ref_type="qr_scan", ref_id=headers["HTTP_X_IDEMPOTENCY_KEY"]).count(),
            1,
        )

    @patch("smart_agri.core.api.viewsets.inventory.TreeCensusService.resolve_variance_alert")
    def test_tree_census_resolve_delegates_to_service_layer(self, mock_resolve):
        crop = Crop.objects.create(name=f"Crop {uuid4().hex[:8]}", mode="Open", is_perennial=True)
        log = DailyLog.objects.create(farm=self.farm, log_date=date.today())
        cohort = BiologicalAssetCohort.objects.create(
            farm=self.farm,
            location=self.location,
            crop=crop,
            batch_name="Batch A",
            quantity=10,
            planted_date=date.today(),
        )
        alert = TreeCensusVarianceAlert.objects.create(
            log=log,
            farm=self.farm,
            location=self.location,
            crop=crop,
            missing_quantity=2,
            reason="Test",
        )
        mock_resolve.return_value = {"alert": alert, "cohort": cohort, "ratoon_cohort": None}

        response = self.client.post(
            f"/api/v1/tree-census-variance-alerts/{alert.id}/resolve/",
            {"cohort_id": cohort.id, "create_ratoon": False, "notes": "service-contract"},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=f"tree-{uuid4().hex}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_resolve.call_count, 1)

    @patch("smart_agri.core.api.reporting.ReportingOrchestrationService.enqueue_or_fallback")
    @patch("smart_agri.core.api.reporting.ReportingOrchestrationService.create_advanced_report_request")
    def test_advanced_report_request_delegates_to_service_layer(self, mock_create, mock_enqueue):
        job = AsyncReportRequest.objects.create(
            created_by=self.user,
            report_type=AsyncReportRequest.REPORT_ADVANCED,
            params={},
        )
        mock_create.return_value = job

        response = self.client.post(
            "/api/v1/advanced-report/requests/",
            {"farm_id": self.farm.id, "start": "2026-01-01", "end": "2026-01-31"},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(mock_create.call_count, 1)
        self.assertEqual(mock_enqueue.call_count, 1)

    @patch("smart_agri.core.api.reporting.ReportingOrchestrationService.enqueue_or_fallback")
    @patch("smart_agri.core.api.reporting.ReportingOrchestrationService.create_advanced_report_request")
    def test_commercial_pdf_request_delegates_to_service_layer(self, mock_create, mock_enqueue):
        job = AsyncReportRequest.objects.create(
            created_by=self.user,
            report_type=AsyncReportRequest.REPORT_COMMERCIAL_PDF,
            params={},
        )
        mock_create.return_value = job

        response = self.client.post(
            "/api/v1/advanced-report/requests/",
            {"farm_id": self.farm.id, "report_type": "commercial_pdf", "format": "pdf"},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(mock_create.call_count, 1)
        self.assertEqual(mock_enqueue.call_count, 1)

    @patch("smart_agri.core.api.reporting.ReportingOrchestrationService.enqueue_or_fallback")
    @patch("smart_agri.core.api.reporting.ReportingOrchestrationService.create_advanced_report_request")
    def test_advanced_report_request_auto_resolves_missing_farm_id(self, mock_create, mock_enqueue):
        job = AsyncReportRequest.objects.create(
            created_by=self.user,
            report_type=AsyncReportRequest.REPORT_ADVANCED,
            params={},
        )
        mock_create.return_value = job

        response = self.client.post(
            "/api/v1/advanced-report/requests/",
            {"start": "2026-01-01", "end": "2026-01-31"},
            format="json",
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(mock_create.call_count, 1)
        self.assertEqual(mock_enqueue.call_count, 1)

    @patch("smart_agri.core.api.reporting.ReportingOrchestrationService.create_advanced_report_request")
    def test_advanced_report_request_rejects_invalid_farm_id(self, mock_create):
        response = self.client.post(
            "/api/v1/advanced-report/requests/",
            {"farm_id": "bad-value", "start": "2026-01-01", "end": "2026-01-31"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("farm_id", response.data)
        self.assertEqual(mock_create.call_count, 0)

    @patch("smart_agri.core.api.reporting.ReportingOrchestrationService.create_advanced_report_request")
    def test_advanced_report_request_rejects_cross_farm_scope(self, mock_create):
        outsider = get_user_model().objects.create_user(
            username=f"outsider-{uuid4().hex[:8]}",
            password="pass1234",
            is_superuser=False,
        )
        self.client.force_authenticate(outsider)
        # Add membership to another farm only, so target farm remains unauthorized.
        other_farm = Farm.objects.create(name=f"Other {uuid4().hex[:6]}", slug=f"other-{uuid4().hex[:6]}", region="R2")
        FarmMembership.objects.create(
            user=outsider,
            farm=other_farm,
            role=FarmMembership.ROLE_CHOICES[-1][0],
        )

        response = self.client.post(
            "/api/v1/advanced-report/requests/",
            {"farm_id": self.farm.id, "start": "2026-01-01", "end": "2026-01-31"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(mock_create.call_count, 0)
