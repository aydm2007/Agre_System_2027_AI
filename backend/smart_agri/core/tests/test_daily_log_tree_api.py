from datetime import date
from decimal import Decimal
import json

from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm, Location
from smart_agri.core.models.crop import Crop, CropVariety
from smart_agri.core.models.planning import CropPlan, CropPlanLocation
from smart_agri.core.models.inventory import TreeCensusVarianceAlert
from smart_agri.core.models.tree import TreeLossReason
from smart_agri.core.models.task import Task
from smart_agri.core.models.activity import Activity
from smart_agri.core.services.loss_prevention import LossPreventionService


class DailyLogTreeVarianceAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="test_agronomist", password="password")
        manager_group, _ = Group.objects.get_or_create(name='مدير النظام')
        self.user.groups.add(manager_group)
        self.client.force_authenticate(user=self.user)

        self.farm = Farm.objects.create(name="Test Farm", slug="test-farm", region="Test")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role='Manager')
        self.location = Location.objects.create(name="Block A", farm=self.farm)
        self.crop =Crop.objects.create(name="Banana", mode="Open", is_perennial=True)
        self.plan = CropPlan.objects.create(
            farm=self.farm,
            name="Plan 2026",
            crop=self.crop,
            start_date=date.today(),
            end_date=date(2026, 12, 31)
        )
        CropPlanLocation.objects.create(crop_plan=self.plan, location=self.location)
        self.variety = CropVariety.objects.create(crop=self.crop, name="Banana Prime")
        self.task = Task.objects.create(
            crop=self.crop,
            stage="Control",
            name="Tree inspection",
            requires_tree_count=True,
            is_perennial_procedure=True,
        )
        self.loss_reason = TreeLossReason.objects.create(
            code="STORM",
            name_en="Storm",
            name_ar="عاصفة"
        )

    def test_daily_log_with_negative_tree_delta_creates_critical_alert(self):
        """
        Axis 11: Submitting a Daily Log that reduces tree count (-2) must
        automatically trigger a CRITICAL TreeCensusVarianceAlert.
        """
        daily_log_url = reverse('dailylogs-list')
        activity_url = reverse('activities-list')

        log_payload = {
            "farm": self.farm.id,
            "log_date": date.today().isoformat(),
        }

        headers = {
            "HTTP_X_IDEMPOTENCY_KEY": "test-idempotency-key-uuidv4",
            "HTTP_X_APP_VERSION": "1.0.0"
        }

        log_response = self.client.post(
            daily_log_url,
            data=json.dumps(log_payload),
            content_type="application/json",
            **headers,
        )
        self.assertEqual(log_response.status_code, status.HTTP_201_CREATED)

        activity_payload = {
            "log_id": log_response.data["id"],
            "location_ids": [self.location.id],
            "crop_plan_id": self.plan.id,
            "crop_id": self.crop.id,
            "task_id": self.task.id,
            "variety_id": self.variety.id,
            "tree_count_delta": -2,
            "activity_tree_count": 2,
            "tree_loss_reason_id": self.loss_reason.id,
        }
        activity_headers = {
            "HTTP_X_IDEMPOTENCY_KEY": "test-idempotency-key-uuidv4-activity",
            "HTTP_X_APP_VERSION": "1.0.0",
        }
        activity_response = self.client.post(
            activity_url,
            data=json.dumps(activity_payload),
            content_type="application/json",
            **activity_headers,
        )
        self.assertEqual(activity_response.status_code, status.HTTP_201_CREATED)
        
        activity = Activity.objects.get(pk=activity_response.data["id"])
        log = activity.log
        alerts_created = LossPreventionService.analyze_tree_census(log)

        self.assertEqual(alerts_created, 1)

        # Verify VarianceAlert was created
        alerts = TreeCensusVarianceAlert.objects.filter(farm=self.farm)
        self.assertEqual(alerts.count(), 1)
        alert = alerts.first()
        self.assertEqual(alert.missing_quantity, 2)
        self.assertEqual(alert.status, TreeCensusVarianceAlert.STATUS_PENDING)
