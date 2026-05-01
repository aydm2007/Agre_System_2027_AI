from django.test import TestCase

from smart_agri.core.api.serializers.planning import CropPlanBudgetLineSerializer
from smart_agri.core.models import Crop, CropPlan, Farm, Season, Task


class CropPlanBudgetUomSerializerTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="UOM Farm", slug="uom-farm", region="North")
        self.crop = Crop.objects.create(name="UOM Crop", mode="Open")
        self.season = Season.objects.create(
            name="2026",
            start_date="2026-01-01",
            end_date="2026-12-31",
            is_active=True,
        )
        self.plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            season=self.season,
            name="UOM Plan",
            start_date="2026-01-10",
            end_date="2026-02-10",
            currency="YER",
        )
        self.task = Task.objects.create(
            crop=self.crop,
            stage="Care",
            name="Irrigation",
        )

    def test_serializer_normalizes_liter_alias_to_canonical_code(self):
        serializer = CropPlanBudgetLineSerializer(
            data={
                "crop_plan": self.plan.id,
                "task": self.task.id,
                "category": "materials",
                "qty_budget": "12",
                "uom": "liter",
                "rate_budget": "250",
                "total_budget": "3000",
                "currency": "YER",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["uom"], "L")
