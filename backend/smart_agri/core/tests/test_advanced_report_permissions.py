from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Activity, Crop, DailyLog, Farm, Task


class AdvancedReportPermissionTests(TestCase):
    def setUp(self):
        self.farm_a = Farm.objects.create(name="Farm A", slug="farm-a", region="north")
        self.farm_b = Farm.objects.create(name="Farm B", slug="farm-b", region="south")

        self.crop = Crop.objects.create(name="Tomato", mode="Open")
        self.task = Task.objects.create(crop=self.crop, stage="Planting", name="Prepare beds")

        self.log_a = DailyLog.objects.create(farm=self.farm_a, log_date=date(2024, 1, 1), notes="A")
        self.log_b = DailyLog.objects.create(farm=self.farm_b, log_date=date(2024, 1, 2), notes="B")

        Activity.objects.create(log=self.log_a, crop=self.crop, task=self.task, team="Team A")
        Activity.objects.create(log=self.log_b, crop=self.crop, task=self.task, team="Team B")

    def test_rejects_user_without_farm_membership(self):
        user = User.objects.create_user("noaccess", password="pass123")
        client = APIClient()
        client.force_authenticate(user)

        resp = client.get("/api/v1/advanced-report/")
        self.assertEqual(resp.status_code, 403)

    def test_limits_data_to_member_farms(self):
        user = User.objects.create_user("member", password="pass123")
        FarmMembership.objects.create(user=user, farm=self.farm_a, role="Manager")
        client = APIClient()
        client.force_authenticate(user)

        resp = client.get("/api/v1/advanced-report/?start=2024-01-01&end=2024-01-10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Filters should be constrained to the user's farms
        self.assertEqual(data["summary"]["filters"]["farms"], [self.farm_a.id])

        # Returned activities should belong only to farm A
        details = data.get("details", [])
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["farm"]["id"], self.farm_a.id)
