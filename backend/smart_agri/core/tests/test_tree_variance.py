from django.test import TestCase

from smart_agri.core.models.inventory import TreeCensusVarianceAlert
from smart_agri.core.models.farm import Farm, Location
from smart_agri.core.models.crop import Crop
from smart_agri.core.models.planning import CropPlan, CropPlanLocation
from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.tree import TreeLossReason
from smart_agri.core.services.loss_prevention import LossPreventionService


class TreeVarianceTests(TestCase):
    def test_loss_prevention_on_tree_census(self):
        farm = Farm.objects.create(name="Sardud Farm", slug="sardud-farm", region="North")
        location = Location.objects.create(name="Block C", farm=farm)
        crop = Crop.objects.create(name="Banana")
        plan = CropPlan.objects.create(
            farm=farm,
            name="Spring 2025",
            crop=crop,
            start_date="2025-01-01",
            end_date="2025-12-31",
        )
        CropPlanLocation.objects.create(crop_plan=plan, location=location)

        log = DailyLog.objects.create(farm=farm, log_date="2025-01-01")
        loss_reason = TreeLossReason.objects.create(
            code="STORM",
            name_en="Storm damage",
            name_ar="ضرر عاصفة",
        )
        activity = Activity.objects.create(
            log=log,
            location=location,
            crop_plan=plan,
            crop=crop,
            tree_count_delta=-5,
            tree_loss_reason=loss_reason,
        )
        self.assertEqual(activity.location_id, location.id)

        alerts_created = LossPreventionService.analyze_tree_census(log)
        self.assertEqual(alerts_created, 1)

        alert = TreeCensusVarianceAlert.objects.get(log=log)
        self.assertEqual(alert.missing_quantity, 5)
        self.assertIn("Storm damage", alert.reason)
        self.assertEqual(alert.status, TreeCensusVarianceAlert.STATUS_PENDING)
