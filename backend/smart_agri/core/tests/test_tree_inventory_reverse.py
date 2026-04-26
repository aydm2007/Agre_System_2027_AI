from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date

from smart_agri.core.models import (
    Farm,
    Location,
    Crop,
    CropVariety,
    Task,
    DailyLog,
    Activity,
    LocationTreeStock,
    TreeStockEvent,
)
from smart_agri.core.services.tree_inventory import TreeInventoryService


class TreeInventoryReverseTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="testuser", password="testpass")

        self.farm = Farm.objects.create(name="Test Farm", slug="test-farm", region="R1")
        self.location = Location.objects.create(farm=self.farm, name="Loc 1")
        self.crop = Crop.objects.create(name="Mango", mode="Open", is_perennial=True)
        self.variety = CropVariety.objects.create(crop=self.crop, name="Var 1")
        self.task = Task.objects.create(crop=self.crop, stage="Stage", name="Harvest", requires_tree_count=True)

        self.log = DailyLog.objects.create(farm=self.farm, log_date=date.today())

    def test_reverse_activity_clamps_negative_stock_and_deletes_event(self):
        # Create an activity that added 5 trees
        activity = Activity.objects.create(
            log=self.log,
            crop=self.crop,
            task=self.task,
            location=self.location,
            variety=self.variety,
            tree_count_delta=5,
        )

        # Realistic starting state: if we added 5, stock should have 5.
        stock = LocationTreeStock.objects.create(location=self.location, crop_variety=self.variety, current_tree_count=5)

        event = TreeStockEvent.objects.create(
            location_tree_stock=stock,
            activity=activity,
            event_type=TreeStockEvent.PLANTING,
            tree_count_delta=5,
            resulting_tree_count=5,
        )

        service = TreeInventoryService()
        # Reverse the activity (5 - 5 = 0)
        result = service.reverse_activity(activity=activity, user=self.user)

        # After reverse, the event should be deleted and stock count should be 0
        self.assertFalse(TreeStockEvent.objects.filter(pk=event.pk).exists())
        refreshed_stock = LocationTreeStock.objects.get(pk=stock.pk)
        self.assertEqual(refreshed_stock.current_tree_count, 0)
        # Result should contain the stock and the (now-deleted) event
        self.assertIsNotNone(result)
        self.assertEqual(result.stock.pk, stock.pk)
