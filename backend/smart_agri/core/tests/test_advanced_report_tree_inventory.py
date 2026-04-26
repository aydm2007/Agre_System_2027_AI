from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from django.db.models.query import QuerySet
from unittest.mock import patch

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import (
    Activity,
    ActivityItem,
    Crop,
    CropVariety,
    DailyLog,
    Farm,
    Item,
    Location,
    LocationTreeStock,
    Task,
)


class AdvancedReportTreeInventoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("tree-report-user", password="secret")
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name="Test Farm", slug="test-farm", region="")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")

        self.location = Location.objects.create(farm=self.farm, name="Block A")
        self.crop = Crop.objects.create(name="نخيل", is_perennial=True)
        self.variety = CropVariety.objects.create(crop=self.crop, name="سكري")
        self.task = Task.objects.create(
            crop=self.crop,
            name="خدمة الري",
            stage="عناية",
            requires_tree_count=True,
            is_perennial_procedure=True,
        )

        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date=date(2024, 8, 1),
            created_by=self.user,
            updated_by=self.user,
        )

        activity = Activity.objects.create(
            log=self.log,
            crop=self.crop,
            task=self.task,
            location=self.location,
            activity_tree_count=45,
            tree_count_delta=5,
            machine_hours=0,
        )
        material_item = Item.objects.create(name='سماد أورجانيك', group='Fertilizer', uom='kg')
        ActivityItem.objects.create(activity=activity, item=material_item, qty=Decimal('0'), uom='kg')

        LocationTreeStock.objects.create(
            location=self.location,
            crop_variety=self.variety,
            current_tree_count=120,
        )

    def test_fetch_with_tree_inventory_succeeds(self):
        original_aggregate = QuerySet.aggregate

        def aggregate_with_nan(self, *args, **kwargs):
            result = original_aggregate(self, *args, **kwargs)
            if {"machine_hours", "materials_total_qty"}.issubset(kwargs.keys()):
                result = dict(result)
                result["machine_hours"] = Decimal("NaN")
                result["materials_total_qty"] = Decimal("NaN")
            return result

        with patch.object(QuerySet, "aggregate", aggregate_with_nan):
            response = self.client.get(
                "/api/v1/advanced-report/",
                {
                    "start": "2024-08-01",
                    "end": "2024-08-02",
                    "farm": str(self.farm.id),
                    "include_tree_inventory": "true",
                    "tree_filters": "{}",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("summary", payload)
        self.assertIn("perennial_insights", payload["summary"])
        metrics = payload["summary"]["metrics"]
        self.assertNotIn("nan", str(metrics["machine_hours"]))
