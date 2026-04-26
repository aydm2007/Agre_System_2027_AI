from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Farm
from smart_agri.core.services.reporting_orchestration_service import ReportingOrchestrationService


class ReportingOrchestrationServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username=f"rep-{uuid4().hex[:8]}",
            password="pass1234",
            is_superuser=False,
        )
        self.superuser = user_model.objects.create_user(
            username=f"rep-admin-{uuid4().hex[:8]}",
            password="pass1234",
            is_superuser=True,
        )
        self.farm = Farm.objects.create(
            name=f"Farm {uuid4().hex[:8]}",
            slug=f"farm-{uuid4().hex[:8]}",
            region="R1",
        )

    def test_resolve_farm_for_alert_rejects_cross_farm_user(self):
        with self.assertRaises(PermissionDenied):
            ReportingOrchestrationService._resolve_farm_for_alert(
                actor=self.user,
                params={"farm_id": self.farm.id},
            )

    def test_resolve_farm_for_alert_allows_member_user(self):
        FarmMembership.objects.create(
            user=self.user,
            farm=self.farm,
            role=FarmMembership.ROLE_CHOICES[-1][0],
        )
        farm = ReportingOrchestrationService._resolve_farm_for_alert(
            actor=self.user,
            params={"farm_id": self.farm.id},
        )
        self.assertEqual(farm.id, self.farm.id)

    def test_resolve_farm_for_alert_allows_superuser(self):
        farm = ReportingOrchestrationService._resolve_farm_for_alert(
            actor=self.superuser,
            params={"farm_id": self.farm.id},
        )
        self.assertEqual(farm.id, self.farm.id)
