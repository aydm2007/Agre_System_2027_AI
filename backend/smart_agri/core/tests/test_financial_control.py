from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from smart_agri.core.models import Activity, ActivityCostSnapshot, CropPlan, Task, DailyLog, Farm, Location, Crop
from smart_agri.core.services.costing import calculate_activity_cost
from smart_agri.core.services.variance import detect_cost_anomalies

class FinancialControlTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Test Farm", slug="test-farm")
        self.location = Location.objects.create(farm=self.farm, name="Field 1", type="Field")
        self.crop = Crop.objects.create(name="Wheat", mode="Open")
        self.task = Task.objects.create(crop=self.crop, name="Harvest", stage="Growth")
        self.plan = CropPlan.objects.create(
            farm=self.farm, 
            crop=self.crop, 
            location=self.location,
            name="Plan 2025",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=90)
        )
        self.log = DailyLog.objects.create(farm=self.farm, log_date=timezone.now().date(), supervisor=None)

    def test_overhead_calculation(self):
        # Create activity with 100000 m2 (10 Ha)
        activity = Activity.objects.create(
            log=self.log,
            crop_plan=self.plan,
            task=self.task,
            location=self.location,
            planted_area=Decimal("100000"),
            planted_uom="m2",
            cost_materials=Decimal("100"),
            cost_labor=Decimal("200"),
            cost_machinery=Decimal("300")
        )
        
        calculate_activity_cost(activity)
        activity.refresh_from_db()
        
        # Overhead: 10 Ha * 50 = 500
        self.assertEqual(activity.cost_overhead, Decimal("500.00"))
        # Total: 0 + 0 + 0 + 500 = 500 (Other costs recalculated to 0 due to no items/rates)
        self.assertEqual(activity.cost_total, Decimal("500.00"))

        # Verify Snapshot
        snapshot = ActivityCostSnapshot.objects.get(activity=activity)
        self.assertEqual(snapshot.cost_overhead, Decimal("500.00"))
        self.assertEqual(snapshot.cost_total, Decimal("500.00"))

    def test_anomaly_detection(self):
        # Create 5 normal activities (Cost ~100)
        # We rely on signals to calculate costs now, so we create normally.
        # However, calculate_activity_cost needs fields populated.
        # We will manually set costs for this test to specific values to control mean,
        # but since signals run, we must ensure they don't overwrite with 0 if data missing.
        # Actually, let's create full activities so signals do their job.
        
        # Scenario: 5 activities with low overhead/cost, 1 with high.
        
        # Normal: 1000m2 = 0.1 Ha -> 5 SAR overhead + 95 materials = 100 total
        for _ in range(5):
            Activity.objects.create(
                log=self.log, crop_plan=self.plan, task=self.task,
                planted_area=Decimal("1000"), planted_uom="m2",
                cost_materials=Decimal("95.00")
            )
        
        # Outlier: 10000m2 = 1 Ha -> 50 SAR overhead + 950 materials = 1000 total
        outlier = Activity.objects.create(
            log=self.log, crop_plan=self.plan, task=self.task,
            planted_area=Decimal("10000"), planted_uom="m2",
            cost_materials=Decimal("950.00")
        )

        anomalies = detect_cost_anomalies(self.plan.id)
        
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]['activity_id'], outlier.id)
        # Expected total: 950 + 50 = 1000
        self.assertEqual(anomalies[0]['cost_total'], Decimal("1000.00"))
        self.assertTrue(anomalies[0]['risk_score'] > 2)
