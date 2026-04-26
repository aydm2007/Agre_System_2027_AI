from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Asset, Farm
from smart_agri.core.models.settings import Supervisor
from smart_agri.core.models.planning import CropPlan


class FrictionlessLogApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("frictionless-user", password="pass123")
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(
            name="Frictionless Farm",
            slug="frictionless-farm",
            region="North",
        )
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")
        self.machine = Asset.objects.create(
            farm=self.farm,
            category="Machinery",
            name="Tractor 01",
        )
        self.other_farm = Farm.objects.create(
            name="Other Farm",
            slug="other-farm",
            region="North",
        )
        self.foreign_supervisor = Supervisor.objects.create(
            farm=self.other_farm,
            name="Foreign Supervisor",
            code="SUP-FOREIGN",
        )
        self.foreign_crop_plan = CropPlan.objects.create(
            farm=self.other_farm,
            name="Foreign Plan",
            start_date="2026-02-01",
            end_date="2026-02-28",
        )

    def _post(self, payload, key="idem-frictionless-1"):
        return self.client.post(
            "/api/v1/frictionless-daily-logs/",
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=key,
        )

    def test_requires_x_idempotency_key_returns_400(self):
        payload = {
            "farm_id": self.farm.id,
            "log_date": "2026-02-28",
            "activity_name": "حراثة",
            "workers_count": 1,
            "shift_hours": "8.0000",
        }
        response = self.client.post("/api/v1/frictionless-daily-logs/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("X-Idempotency-Key", str(response.data))

    @patch("smart_agri.core.api.viewsets.frictionless_log.FrictionlessDailyLogService.process_technical_log")
    def test_machine_requires_dipstick(self, service_mock):
        payload = {
            "farm_id": self.farm.id,
            "log_date": "2026-02-28",
            "activity_name": "حراثة",
            "workers_count": 3,
            "shift_hours": "8.0000",
            "machine_asset_id": self.machine.id,
            "machine_hours": "4.0000",
            "dipstick_start_liters": "0",
            "dipstick_end_liters": "0",
        }
        response = self._post(payload, key="idem-frictionless-dipstick")
        self.assertEqual(response.status_code, 400)
        self.assertIn("dipstick", response.json())
        service_mock.assert_not_called()

    @patch("smart_agri.core.api.viewsets.frictionless_log.FrictionlessDailyLogService.process_technical_log")
    def test_machine_with_dipstick_succeeds(self, service_mock):
        service_mock.return_value = {"daily_log_id": 1, "diesel_result": "OK"}
        payload = {
            "farm_id": self.farm.id,
            "log_date": "2026-02-28",
            "activity_name": "حراثة",
            "workers_count": 3,
            "shift_hours": "8.0000",
            "machine_asset_id": self.machine.id,
            "machine_hours": "4.0000",
            "dipstick_start_liters": "100.0000",
            "dipstick_end_liters": "94.0000",
        }
        response = self._post(payload, key="idem-frictionless-success")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["daily_log_id"], 1)
        service_mock.assert_called_once()

    @patch("smart_agri.core.api.viewsets.frictionless_log.FrictionlessDailyLogService.process_technical_log")
    def test_without_machine_does_not_require_dipstick(self, service_mock):
        service_mock.return_value = {"daily_log_id": 2, "diesel_result": "SKIPPED_NO_MACHINE"}
        payload = {
            "farm_id": self.farm.id,
            "log_date": "2026-02-28",
            "activity_name": "تنظيف",
            "workers_count": 2,
            "shift_hours": "6.0000",
        }
        response = self._post(payload, key="idem-frictionless-no-machine")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["daily_log_id"], 2)
        service_mock.assert_called_once()

    @patch("smart_agri.core.api.viewsets.frictionless_log.FrictionlessDailyLogService.process_technical_log")
    def test_duplicate_key_replays_single_write(self, service_mock):
        service_mock.return_value = {"daily_log_id": 99, "diesel_result": "OK"}
        payload = {
            "farm_id": self.farm.id,
            "log_date": "2026-02-28",
            "activity_name": "حراثة",
            "workers_count": 2,
            "shift_hours": "8.0000",
        }
        key = "idem-frictionless-replay"
        response_first = self._post(payload, key=key)
        response_second = self._post(payload, key=key)
        self.assertEqual(response_first.status_code, 201)
        self.assertEqual(response_second.status_code, 201)
        self.assertEqual(response_first.json(), response_second.json())
        service_mock.assert_called_once()

    @patch("smart_agri.core.api.viewsets.frictionless_log.FrictionlessDailyLogService.process_technical_log")
    def test_supervisor_outside_farm_rejected_400(self, service_mock):
        payload = {
            "farm_id": self.farm.id,
            "log_date": "2026-02-28",
            "activity_name": "حراثة",
            "workers_count": 1,
            "shift_hours": "8.0000",
            "supervisor_id": self.foreign_supervisor.id,
        }
        response = self._post(payload, key="idem-frictionless-foreign-supervisor")
        self.assertEqual(response.status_code, 400)
        self.assertIn("supervisor_id", response.json())
        service_mock.assert_not_called()

    @patch("smart_agri.core.api.viewsets.frictionless_log.FrictionlessDailyLogService.process_technical_log")
    def test_crop_plan_outside_farm_rejected_400(self, service_mock):
        payload = {
            "farm_id": self.farm.id,
            "log_date": "2026-02-28",
            "activity_name": "حراثة",
            "workers_count": 1,
            "shift_hours": "8.0000",
            "crop_plan_id": self.foreign_crop_plan.id,
        }
        response = self._post(payload, key="idem-frictionless-foreign-crop-plan")
        self.assertEqual(response.status_code, 400)
        self.assertIn("crop_plan_id", response.json())
        service_mock.assert_not_called()
