from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.core.models.crop import Crop
from smart_agri.core.models.farm import Farm, Location
from smart_agri.core.models.planning import CropPlan, CropPlanLocation


class CropPlanFiltersApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            username="crop-plan-filter-admin",
            email="crop-plan-filter@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(self.user)
        self.farm = Farm.objects.create(name="Crop Plan Filter Farm", slug="crop-plan-filter-farm", region="R1")
        self.location = Location.objects.create(farm=self.farm, name="Block A")
        self.other_location = Location.objects.create(farm=self.farm, name="Block B")
        self.crop = Crop.objects.create(name="Filter Crop", mode="Open")

    def test_location_filter_uses_plan_locations_without_500(self):
        plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name="Scoped Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        CropPlanLocation.objects.create(crop_plan=plan, location=self.location)

        other_plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name="Other Plan",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        CropPlanLocation.objects.create(crop_plan=other_plan, location=self.other_location)

        response = self.client.get(
            "/api/v1/crop-plans/",
            {"farm_id": self.farm.id, "location_id": self.location.id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        rows = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], plan.id)
