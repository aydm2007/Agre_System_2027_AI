from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from smart_agri.core.models import Activity, ActivityCostSnapshot, Crop, DailyLog, Farm, Location, Task
from smart_agri.core.models.planning import CropPlan, CropPlanLocation
from smart_agri.core.services.costing import calculate_activity_cost


class ActivityCostSnapshotIntegrityTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Snapshot Farm", slug="snapshot-farm", region="A")
        self.location = Location.objects.create(farm=self.farm, name="Zone 1", type="Field")
        self.crop = Crop.objects.create(name="Mango Snapshot", mode="Open")
        self.task = Task.objects.create(crop=self.crop, name="Tree Service", stage="Trees")
        self.plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name="Snapshot Plan",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            status="active",
        )
        CropPlanLocation.objects.create(crop_plan=self.plan, location=self.location)
        self.log = DailyLog.objects.create(farm=self.farm, log_date=timezone.now().date())

    def test_calculate_activity_cost_reuses_single_active_snapshot(self):
        activity = Activity.objects.create(
            log=self.log,
            crop_plan=self.plan,
            crop=self.crop,
            task=self.task,
            planted_area=Decimal("100000"),
            planted_uom="m2",
            cost_materials=Decimal("100.0000"),
            cost_labor=Decimal("200.0000"),
            cost_machinery=Decimal("300.0000"),
        )

        snapshot = ActivityCostSnapshot.objects.create(
            activity=activity,
            crop_plan=self.plan,
            task=self.task,
            cost_total=Decimal("10.0000"),
            currency="YER",
        )

        calculate_activity_cost(activity)

        active_snapshots = list(
            ActivityCostSnapshot.objects.filter(activity=activity, deleted_at__isnull=True).order_by("-id")
        )
        self.assertEqual(len(active_snapshots), 1)
        self.assertEqual(active_snapshots[0].id, snapshot.id)
        self.assertEqual(active_snapshots[0].cost_total, Decimal("500.00"))
