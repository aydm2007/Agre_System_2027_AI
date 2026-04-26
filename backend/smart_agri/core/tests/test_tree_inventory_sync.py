from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from smart_agri.core.models import (
    Activity,
    ActivityLocation,
    Crop,
    CropVariety,
    DailyLog,
    Farm,
    Location,
    LocationTreeStock,
    Task,
    TreeLossReason,
    TreeStockEvent,
)
from smart_agri.core.services import TreeInventoryService


class TreeInventorySyncTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user("tester", password="pass123")

        self.farm = Farm.objects.create(name="Test Farm", slug="test-farm", region="A")
        self.primary_location = Location.objects.create(
            farm=self.farm,
            name="Location A",
            type="Orchard",
        )
        self.secondary_location = Location.objects.create(
            farm=self.farm,
            name="Location B",
            type="Orchard",
        )

        self.crop = Crop.objects.create(name="نخيل", mode="Open", is_perennial=True)
        self.variety = CropVariety.objects.create(crop=self.crop, name="برحي")
        self.task = Task.objects.create(
            crop=self.crop,
            stage="Service",
            name="عناية بالأشجار",
            requires_tree_count=True,
            is_perennial_procedure=True,
        )

        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

        self.loss_reason = TreeLossReason.objects.create(
            code="pest",
            name_en="Pest",
            name_ar="آفة",
        )

        self.service = TreeInventoryService()

    def _create_activity(self, **overrides) -> Activity:
        payload = {
            "log": self.log,
            "crop": self.crop,
            "task": self.task,
            "location": self.primary_location,
            "variety": self.variety,
            "tree_count_delta": 10,
            "activity_tree_count": 10,
            "tree_loss_reason": None,
            "created_by": self.user,
            "updated_by": self.user,
        }
        payload.update(overrides)
        return Activity.objects.create(**payload)

    def _reconcile(self, activity: Activity, *, previous_delta=0, previous_activity_tree_count=None):
        delta_change = (activity.tree_count_delta or 0) - previous_delta
        tree_count_change = None
        if previous_activity_tree_count is not None or activity.activity_tree_count is not None:
            tree_count_change = (activity.activity_tree_count or 0) - (previous_activity_tree_count or 0)

        return self.service.reconcile_activity(
            activity=activity,
            user=self.user,
            delta_change=delta_change,
            previous_delta=previous_delta,
            activity_tree_count_change=tree_count_change,
            previous_activity_tree_count=previous_activity_tree_count,
        )

    def test_reconcile_activity_updates_existing_event_without_duplicates(self):
        activity = self._create_activity()
        result = self._reconcile(activity, previous_activity_tree_count=0)

        self.assertIsNotNone(result)
        self.assertEqual(result.stock.current_tree_count, 10)
        self.assertEqual(TreeStockEvent.objects.filter(activity=activity).count(), 1)

        previous_delta = activity.tree_count_delta
        previous_tree_count = activity.activity_tree_count
        existing_event_id = result.event.pk

        activity.tree_count_delta = 7
        activity.activity_tree_count = 7
        activity.save(update_fields=["tree_count_delta", "activity_tree_count", "updated_at"])

        update_result = self._reconcile(
            activity,
            previous_delta=previous_delta,
            previous_activity_tree_count=previous_tree_count,
        )

        self.assertIsNotNone(update_result)
        self.assertEqual(update_result.event.pk, existing_event_id)
        self.assertEqual(update_result.event.tree_count_delta, 7)
        self.assertEqual(update_result.event.resulting_tree_count, 7)
        stock = LocationTreeStock.objects.get(pk=update_result.stock.pk)
        self.assertEqual(stock.current_tree_count, 7)
        self.assertEqual(TreeStockEvent.objects.filter(activity=activity).count(), 1)

    def test_reconcile_activity_with_defaults_updates_existing_event(self):
        activity = self._create_activity()
        initial_result = self.service.reconcile_activity(activity=activity, user=self.user)

        self.assertIsNotNone(initial_result)
        self.assertEqual(TreeStockEvent.objects.filter(activity=activity).count(), 1)

        activity.tree_count_delta = 6
        activity.activity_tree_count = 6
        activity.save(update_fields=["tree_count_delta", "activity_tree_count", "updated_at"])

        update_result = self.service.reconcile_activity(activity=activity, user=self.user)

        self.assertIsNotNone(update_result)
        self.assertEqual(TreeStockEvent.objects.filter(activity=activity).count(), 1)
        self.assertEqual(update_result.event.tree_count_delta, 6)
        self.assertEqual(update_result.event.resulting_tree_count, 6)
        self.assertEqual(update_result.stock.current_tree_count, 6)

    def test_reconcile_activity_moves_event_when_location_changes(self):
        activity = self._create_activity()
        initial_result = self._reconcile(activity, previous_activity_tree_count=0)

        original_stock = LocationTreeStock.objects.get(pk=initial_result.stock.pk)
        self.assertEqual(original_stock.current_tree_count, 10)
        original_event_id = initial_result.event.pk

        activity.location = self.secondary_location
        ActivityLocation.objects.filter(activity=activity).update(location=self.secondary_location)
        activity._legacy_location = self.secondary_location
        activity._legacy_location_id = self.secondary_location.id

        move_result = self._reconcile(
            activity,
            previous_delta=10,
            previous_activity_tree_count=10,
        )

        original_stock.refresh_from_db()
        self.assertEqual(original_stock.current_tree_count, 0)

        new_stock = LocationTreeStock.objects.get(pk=move_result.stock.pk)
        self.assertEqual(new_stock.location_id, self.secondary_location.id)
        self.assertEqual(new_stock.current_tree_count, 10)
        self.assertEqual(move_result.event.pk, original_event_id)
        self.assertEqual(move_result.event.location_tree_stock_id, new_stock.pk)
        self.assertEqual(move_result.event.event_type, TreeStockEvent.TRANSFER)

    def test_reconcile_activity_marks_transfer_when_variety_changes(self):
        activity = self._create_activity()
        initial_result = self._reconcile(activity, previous_activity_tree_count=0)

        original_stock = LocationTreeStock.objects.get(pk=initial_result.stock.pk)
        self.assertEqual(original_stock.current_tree_count, 10)

        new_variety = CropVariety.objects.create(crop=self.crop, name="سكري")

        previous_delta = activity.tree_count_delta
        previous_tree_count = activity.activity_tree_count

        activity.variety = new_variety
        activity.save(update_fields=["crop_variety", "updated_at"])

        move_result = self._reconcile(
            activity,
            previous_delta=previous_delta,
            previous_activity_tree_count=previous_tree_count,
        )

        original_stock.refresh_from_db()
        self.assertEqual(original_stock.current_tree_count, 0)

        new_stock = LocationTreeStock.objects.get(pk=move_result.stock.pk)
        self.assertEqual(new_stock.crop_variety_id, new_variety.id)
        self.assertEqual(new_stock.current_tree_count, 10)
        self.assertEqual(move_result.event.event_type, TreeStockEvent.TRANSFER)

    def test_reverse_activity_restores_stock_balance(self):
        base_activity = self._create_activity()
        self._reconcile(base_activity, previous_activity_tree_count=0)

        activity = self._create_activity(
            tree_count_delta=-5,
            activity_tree_count=5,
            tree_loss_reason=self.loss_reason,
        )
        initial = self._reconcile(activity, previous_activity_tree_count=0)

        stock = LocationTreeStock.objects.get(pk=initial.stock.pk)
        self.assertEqual(stock.current_tree_count, 5)
        self.assertTrue(TreeStockEvent.objects.filter(activity=activity).exists())

        reversal = self.service.reverse_activity(activity=activity, user=self.user)
        self.assertIsNotNone(reversal)

        stock.refresh_from_db()
        self.assertEqual(stock.current_tree_count, 10)
        self.assertFalse(TreeStockEvent.objects.filter(activity=activity).exists())
