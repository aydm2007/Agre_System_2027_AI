from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Activity, Crop, DailyLog, Farm, Task


class AdvancedReportPaginationTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Farm A", slug="farm-a", region="north")
        self.crop = Crop.objects.create(name="Tomato", mode="Open")
        self.task = Task.objects.create(crop=self.crop, stage="Planting", name="Prepare beds")
        # Create 12 activities to test pagination windowing
        for i in range(12):
            log = DailyLog.objects.create(
                farm=self.farm,
                log_date=date(2024, 1, 1) + timedelta(days=i),
                notes=f"log {i}",
            )
            Activity.objects.create(log=log, crop=self.crop, task=self.task, team=f"Team {i}")

        self.user = User.objects.create_user("member", password="pass123")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_details_limit_and_offset(self):
        resp = self.client.get(
            "/api/v1/advanced-report/?details_limit=5&details_offset=0&start=2024-01-01&end=2024-02-01&section_scope=summary&section_scope=activities"
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        details = payload.get("details", [])
        meta = payload.get("details_meta", {})
        total = meta.get("total") or 0
        self.assertGreaterEqual(total, 12)
        self.assertEqual(len(details), min(5, total))
        self.assertTrue(meta.get("has_more"))
        self.assertEqual(meta.get("offset"), 0)

        resp2 = self.client.get(
            "/api/v1/advanced-report/?details_limit=5&details_offset=5&section_scope=summary&section_scope=activities"
        )
        self.assertEqual(resp2.status_code, 200)
        payload2 = resp2.json()
        details2 = payload2.get("details", [])
        meta2 = payload2.get("details_meta", {})
        self.assertLessEqual(len(details2), 5)
        self.assertTrue(meta2.get("has_more") in (True, False))
        self.assertEqual(meta2.get("offset"), 5)

        resp3 = self.client.get(
            "/api/v1/advanced-report/?details_limit=5&details_offset=10&section_scope=summary&section_scope=activities"
        )
        self.assertEqual(resp3.status_code, 200)
        payload3 = resp3.json()
        details3 = payload3.get("details", [])
        meta3 = payload3.get("details_meta", {})
        self.assertLessEqual(len(details3), 5)
        self.assertFalse(meta3.get("has_more"))
        self.assertEqual(meta3.get("offset"), 10)
