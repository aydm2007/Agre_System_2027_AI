from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import IntegrityError
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
)
from smart_agri.core.services import TreeInventoryService


class TreeInventoryConcurrencyTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user("tester", password="pass123")
        self.farm = Farm.objects.create(name="Palm Farm", slug="palm-farm", region="South")
        self.location = Location.objects.create(farm=self.farm, name="Block A", type="Orchard")
        self.crop = Crop.objects.create(name="نخيل", mode="Open", is_perennial=True)
        self.variety = CropVariety.objects.create(crop=self.crop, name="سكري")
        self.task = Task.objects.create(
            crop=self.crop,
            stage="Service",
            name="رعاية",
            requires_tree_count=True,
            is_perennial_procedure=True,
        )
        self.log = DailyLog.objects.create(farm=self.farm, log_date=date.today())
        self.activity = Activity.objects.create(
            log=self.log,
            crop=self.crop,
            task=self.task,
            location=self.location,
            variety=self.variety,
            tree_count_delta=5,
            activity_tree_count=5,
        )
        self.service = TreeInventoryService()

    def test_lock_location_stock_handles_race_condition(self):
        original_create = LocationTreeStock._base_manager.create

        def fake_create(*args, **kwargs):
            # Simulate another transaction creating the record before the insert finishes.
            if not LocationTreeStock.objects.filter(location=self.location, crop_variety=self.variety).exists():
                original_create(*args, **kwargs)
            raise IntegrityError("duplicate key value violates unique constraint")

        with mock.patch.object(LocationTreeStock.objects, "create", side_effect=fake_create):
            stock = self.service._lock_location_stock(self.activity)

        self.assertIsNotNone(stock)
        self.assertEqual(stock.location_id, self.location.id)
        self.assertEqual(stock.crop_variety_id, self.variety.id)
        # Ensure only one record exists for the location/variety pair.
        self.assertEqual(
            LocationTreeStock.objects.filter(location=self.location, crop_variety=self.variety).count(),
            1,
        )
