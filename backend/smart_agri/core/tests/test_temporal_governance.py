from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from smart_agri.core.models import Farm, Crop, Task, CropTemplate, CropTemplateTask, CropPlan, Activity, DailyLog
from smart_agri.core.models.report import VarianceAlert
from smart_agri.core.services.planning_timeline_service import PlanningTimelineService
from smart_agri.core.services.activity_service import ActivityService

User = get_user_model()

class TemporalGovernanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="password")
        self.farm = Farm.objects.create(name="Temporal Farm")
        self.farm.settings.enable_timed_plan_compliance = True
        self.farm.settings.save()
        
        self.crop = Crop.objects.create(name="Temporal Crop")
        self.task = Task.objects.create(name="Tilling", crop=self.crop)
        
        self.template = CropTemplate.objects.create(name="Timed Template", crop=self.crop)
        self.ttask = CropTemplateTask.objects.create(
            template=self.template,
            task=self.task,
            days_offset=2, # Starts on Day 2
            duration_days=3 # Lasts until Day 4 (2+3-1)
        )
        
        self.log = DailyLog.objects.create(farm=self.farm, log_date=timezone.now().date())

    def test_crop_plan_timeline_generation(self):
        """Verify that creating a CropPlan from template generates PlannedActivities with dates."""
        start_date = timezone.now().date()
        plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            template=self.template,
            start_date=start_date,
            end_date=start_date + timedelta(days=30),
            name="Precision Plan"
        )
        
        # Signal should have triggered generation
        planned = plan.planned_activities.filter(task=self.task).first()
        self.assertIsNotNone(planned)
        self.assertEqual(planned.expected_date_start, start_date + timedelta(days=2))
        self.assertEqual(planned.expected_date_end, start_date + timedelta(days=4))

    def test_schedule_variance_detection(self):
        """Verify that a late activity triggers a VarianceAlert when compliance is enabled."""
        start_date = timezone.now().date() - timedelta(days=10) # Plan started 10 days ago
        plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            template=self.template,
            start_date=start_date,
            end_date=start_date + timedelta(days=30),
            name="Delayed Execution Plan"
        )
        
        # Expected window was [start+2, start+4] (i.e. 8 days ago to 6 days ago)
        # We record it TODAY (8/10 days late)
        
        activity_data = {
            'log_id': self.log.id,
            'task_id': self.task.id,
            'crop_plan_id': plan.id,
            'activity_date': timezone.now().date(),
            'cost_total': Decimal('100.00')
        }
        
        # This should link and trigger variance
        result = ActivityService.maintain_activity(self.user, activity_data)
        self.assertTrue(result.success)
        
        # Check for VarianceAlert
        alert = VarianceAlert.objects.filter(
            farm=self.farm,
            category=VarianceAlert.CATEGORY_SCHEDULE_DEVIATION
        ).first()
        
        self.assertIsNotNone(alert)
        self.assertIn("انحراف تخطيطي", alert.alert_message)
        self.assertEqual(alert.status, VarianceAlert.ALERT_STATUS_UNINVESTIGATED)
