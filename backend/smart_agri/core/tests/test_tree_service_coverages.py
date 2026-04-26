from datetime import date

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from smart_agri.core.models import (
    Activity,
    Crop,
    CropVariety,
    DailyLog,
    Farm,
    Location,
    LocationTreeStock,
    Task,
    TreeServiceCoverage,
)
from smart_agri.core.services.tree_inventory import TreeInventoryService


class TreeServiceCoverageTestCase(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Farm", slug="farm", region="R")
        self.location = Location.objects.create(farm=self.farm, name="Block 1")
        self.crop = Crop.objects.create(name="Palm", mode="Open")
        self.variety = CropVariety.objects.create(crop=self.crop, name="Sukkary")
        self.task = Task.objects.create(crop=self.crop, stage="Care", name="Irrigation")
        self.log = DailyLog.objects.create(farm=self.farm, log_date=date.today(), notes="")
        self.activity = Activity.objects.create(
            log=self.log,
            crop=self.crop,
            task=self.task,
            location=self.location,
            variety=self.variety,
        )
        self.stock = LocationTreeStock.objects.create(
            location=self.location,
            crop_variety=self.variety,
            current_tree_count=10,
        )

    def test_model_rejects_service_count_above_stock(self):
        with self.assertRaises(ValidationError):
            TreeServiceCoverage.objects.create(
                activity=self.activity,
                location=self.location,
                crop_variety=self.variety,
                trees_covered=11,
                service_type=TreeServiceCoverage.GENERAL,
                farm=self.farm,  # Required field
            )

    def test_sync_service_coverages_rejects_invalid_payload(self):
        service = TreeInventoryService()

        with self.assertRaises(ValidationError):
            service.sync_service_coverages(
                activity=self.activity,
                entries=[
                    {
                        "location": self.location,
                        "crop_variety": self.variety,
                        "service_count": 12,  # Logic converts this to trees_covered
                        "service_type": TreeServiceCoverage.GENERAL,
                    }
                ],
            )

    def test_normalise_management_command_aligns_scope_and_counts(self):
        coverage = TreeServiceCoverage.objects.create(
            activity=self.activity,
            location=self.location,
            crop_variety=self.variety,
            trees_covered=5,
            service_type=TreeServiceCoverage.IRRIGATION,
            target_scope=TreeServiceCoverage.IRRIGATION, # This looks like an enum mismatch in original test too?
            farm=self.farm,
        )

        # Simulate legacy dirty data by bypassing model validation.
        TreeServiceCoverage.objects.filter(pk=coverage.pk).update(
            target_scope="",
            service_type="",
        )

        coverage.refresh_from_db()
        coverage.refresh_from_db()
        self.assertEqual(coverage.target_scope, "")
        self.assertEqual(coverage.service_type, "")
        self.assertEqual(coverage.trees_covered, 5)

        call_command("normalize_tree_service_coverages", "--dry-run")
        coverage.refresh_from_db()
        # Dry-run should keep legacy data unchanged.
        self.assertEqual(coverage.target_scope, "")
        self.assertEqual(coverage.service_type, "")
        self.assertEqual(coverage.trees_covered, 5)

        call_command("normalize_tree_service_coverages")
        coverage.refresh_from_db()

        self.assertEqual(coverage.target_scope, TreeServiceCoverage.GENERAL)
        self.assertEqual(coverage.service_type, TreeServiceCoverage.GENERAL)
        self.assertEqual(coverage.trees_covered, 5)
