# import unittest
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from smart_agri.core.models import (
    Activity,
    Crop,
    CropVariety,
    DailyLog,
    Farm,
    Location,
    LocationTreeStock,
    Task,
    TreeProductivityStatus,
    TreeStockEvent,
)
from smart_agri.core.models.log import AuditLog
from smart_agri.core.services import TreeInventoryService


class TreeInventoryServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="auditor", password="test123")
        self.farm = Farm.objects.create(name="Farm A", slug="farm-a", region="north")
        self.location = Location.objects.create(farm=self.farm, name="Orchard 1", type="Orchard")
        self.other_location = Location.objects.create(farm=self.farm, name="Orchard 2", type="Orchard")
        self.crop = Crop.objects.create(name="نخيل", mode="Open", is_perennial=True)
        self.variety = CropVariety.objects.create(crop=self.crop, name="Barhi")
        self.statuses = {
            code: TreeProductivityStatus.objects.create(
                code=code,
                name_en=code.title(),
                name_ar=code,
                description="",
            )
            for code in ("juvenile", "productive", "declining", "dormant")
        }
        self.service = TreeInventoryService()

    def test_manual_adjustment_creates_event_and_updates_status(self):
        planting = date.today() - timedelta(days=6 * 365)
        result = self.service.manual_adjustment(
            location=self.location,
            variety=self.variety,
            resulting_tree_count=80,
            planting_date=planting,
            source="Field survey",
            reason="Physical recount",
            notes="audit batch 2024",
            user=self.user,
        )

        self.assertEqual(result.stock.current_tree_count, 80)
        self.assertIsNotNone(result.event)
        self.assertEqual(result.event.tree_count_delta, 80)
        self.assertEqual(result.event.event_type, TreeStockEvent.ADJUSTMENT)
        self.assertIn("Physical recount", result.event.notes)
        self.assertEqual(result.stock.productivity_status.code, "productive")
        audit = AuditLog.objects.filter(
            action="TREE_STOCK_MANUAL_ADJUSTMENT",
            model="LocationTreeStock",
            object_id=str(result.stock.pk),
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.reason, "Physical recount")
        self.assertEqual(audit.old_payload.get("current_tree_count"), 0)
        self.assertEqual(audit.new_payload.get("current_tree_count"), 80)

    def test_manual_adjustment_with_delta_updates_existing_stock(self):
        stock = LocationTreeStock.objects.create(
            location=self.location,
            crop_variety=self.variety,
            current_tree_count=50,
            planting_date=date.today() - timedelta(days=8 * 365),
            productivity_status=self.statuses["productive"],
        )
        baseline_events = TreeStockEvent.objects.count()

        result = self.service.manual_adjustment(
            stock=stock,
            delta=-10,
            reason="Pruning loss",
            user=self.user,
        )

        self.assertEqual(result.stock.current_tree_count, 40)
        self.assertEqual(result.event.tree_count_delta, -10)
        self.assertEqual(result.event.event_type, TreeStockEvent.ADJUSTMENT)
        self.assertEqual(result.stock.productivity_status.code, "productive")
        self.assertEqual(TreeStockEvent.objects.count(), baseline_events + 1)
        latest_event = TreeStockEvent.objects.order_by("-id").first()
        self.assertIsNotNone(latest_event)
        self.assertEqual(latest_event.pk, result.event.pk)
        audit = AuditLog.objects.filter(
            action="TREE_STOCK_MANUAL_ADJUSTMENT",
            model="LocationTreeStock",
            object_id=str(stock.pk),
        ).order_by("-timestamp").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.old_payload.get("current_tree_count"), 50)
        self.assertEqual(audit.new_payload.get("current_tree_count"), 40)
        self.assertEqual(audit.new_payload.get("delta"), -10)

    def test_manual_adjustment_rejects_negative_resulting_count(self):
        with self.assertRaises(ValidationError):
            self.service.manual_adjustment(
                location=self.location,
                variety=self.variety,
                resulting_tree_count=-1,
                reason="Invalid recount",
                user=self.user,
            )

    def test_reconcile_activity_accepts_extended_keywords(self):
        log = DailyLog.objects.create(farm=self.farm, log_date=date.today())
        task = Task.objects.create(
            crop=self.crop,
            stage="maintenance",
            name="Irrigation",
            requires_tree_count=False,
        )
        activity = Activity.objects.create(
            log=log,
            crop=self.crop,
            task=task,
            location=self.location,
            variety=self.variety,
            tree_count_delta=5,
        )

        result = self.service.reconcile_activity(
            activity=activity,
            delta_change=2,
            previous_delta=1,
            activity_tree_count_change=4,
            previous_activity_tree_count=6,
            previous_location=self.location,
            previous_variety=self.variety,
            user=self.user,
        )

        self.assertIsNone(result)

    def test_refresh_productivity_status_updates_declining_and_dormant(self):
        old_stock = LocationTreeStock.objects.create(
            location=self.location,
            crop_variety=self.variety,
            current_tree_count=90,
            planting_date=date.today() - timedelta(days=22 * 365),
            productivity_status=self.statuses["productive"],
        )
        dormant_stock = LocationTreeStock.objects.create(
            location=self.other_location,
            crop_variety=self.variety,
            current_tree_count=0,
            planting_date=date.today() - timedelta(days=365),
            productivity_status=self.statuses["productive"],
        )

        result = self.service.refresh_productivity_status(
            queryset=LocationTreeStock.objects.filter(pk__in=[old_stock.pk, dormant_stock.pk]),
            batch_size=1,
        )

        self.assertEqual(result["processed"], 2)
        old_stock.refresh_from_db()
        dormant_stock.refresh_from_db()
        self.assertEqual(old_stock.productivity_status.code, "declining")
        self.assertEqual(dormant_stock.productivity_status.code, "dormant")
        self.assertGreaterEqual(result["updated"], 1)

