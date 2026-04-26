from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.test import APITestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import DailyLog, Farm


class DailyLogActionErrorMappingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="daily-action-user",
            email="daily-action-user@example.com",
            password="pass123",
        )
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name="Action Farm", slug="action-farm", region="North")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")

        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date="2026-02-28",
            created_by=self.user,
            updated_by=self.user,
            status=DailyLog.STATUS_DRAFT,
        )
        self.url = f"/api/v1/daily-logs/{self.log.id}/submit/"

    def _submit(self, key):
        return self.client.post(self.url, {}, format="json", HTTP_X_IDEMPOTENCY_KEY=key)

    @patch("smart_agri.core.services.log_approval_service.LogApprovalService.submit_log")
    def test_action_permission_denied_maps_403(self, submit_mock):
        submit_mock.side_effect = DjangoPermissionDenied("لا تملك الصلاحية")
        response = self._submit("idem-submit-403")
        self.assertEqual(response.status_code, 403)
        self.assertIn("detail", response.data)

    @patch("smart_agri.core.services.log_approval_service.LogApprovalService.submit_log")
    def test_action_validation_error_maps_400(self, submit_mock):
        submit_mock.side_effect = DjangoValidationError("بيانات غير صالحة")
        response = self._submit("idem-submit-400")
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)

    @patch("smart_agri.core.services.log_approval_service.LogApprovalService.submit_log")
    def test_action_unexpected_error_no_internal_leak_500(self, submit_mock):
        submit_mock.side_effect = RuntimeError("secret-db-error")
        response = self._submit("idem-submit-500")
        self.assertEqual(response.status_code, 500)
        self.assertIn("detail", response.data)
        self.assertNotIn("secret-db-error", str(response.data["detail"]))
