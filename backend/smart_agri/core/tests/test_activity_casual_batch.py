from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from smart_agri.core.models import Activity, Crop, DailyLog, Farm, LaborRate, Task
from smart_agri.core.models.activity import ActivityEmployee
from smart_agri.core.models.hr import Employee, EmploymentCategory, Timesheet
from smart_agri.core.services.activity_service import ActivityService


class ActivityCasualBatchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="casual-batch", password="123456")
        self.farm = Farm.objects.create(name="Batch Farm", slug="batch-farm", region="north")
        self.crop = Crop.objects.create(name="Wheat")
        self.task = Task.objects.create(crop=self.crop, stage="Care", name="Weeding")
        self.log = DailyLog.objects.create(farm=self.farm, log_date=timezone.localdate(), created_by=self.user)
        self.activity = Activity.objects.create(log=self.log, task=self.task, crop=self.crop, created_by=self.user)
        LaborRate.objects.create(
            farm=self.farm,
            role_name="عامل يومي",
            daily_rate=Decimal("3000.0000"),
            cost_per_hour=Decimal("0.0000"),
            effective_date=timezone.localdate(),
        )

    def test_sync_employees_allows_casual_batch_without_employee_identity(self):
        ActivityService._sync_employees(
            activity=self.activity,
            employees_payload=[
                {
                    "labor_type": "CASUAL_BATCH",
                    "workers_count": "10",
                    "surrah_share": "1.0",
                    "labor_batch_label": "مقاولة حصاد",
                }
            ],
        )
        detail = ActivityEmployee.objects.get(activity=self.activity)
        self.assertIsNone(detail.employee_id)
        self.assertEqual(detail.labor_type, ActivityEmployee.LABOR_CASUAL_BATCH)
        self.assertEqual(detail.workers_count, Decimal("10.00"))
        self.assertEqual(detail.surrah_share, Decimal("10.00"))
        self.assertEqual(detail.wage_cost, Decimal("30000.00"))
        self.assertEqual(Timesheet.objects.filter(activity=self.activity).count(), 0)

    def test_sync_employees_registered_still_creates_timesheet(self):
        employee = Employee.objects.create(
            farm=self.farm,
            first_name="Ali",
            last_name="Worker",
            employee_id="EMP-BATCH-001",
            role="Worker",
            category=EmploymentCategory.CASUAL,
            payment_mode="SURRA",
            shift_rate=Decimal("2500.0000"),
        )
        ActivityService._sync_employees(
            activity=self.activity,
            employees_payload=[
                {
                    "employee_id": employee.id,
                    "surrah_share": "1.0",
                }
            ],
        )
        detail = ActivityEmployee.objects.get(activity=self.activity, employee=employee)
        self.assertEqual(detail.labor_type, ActivityEmployee.LABOR_REGISTERED)
        self.assertEqual(detail.wage_cost, Decimal("2500.00"))
        self.assertEqual(Timesheet.objects.filter(activity=self.activity, employee=employee).count(), 1)

    def test_maintain_activity_without_labor_sets_zero_days_spent(self):
        activity_log = DailyLog.objects.create(
            farm=self.farm,
            log_date=timezone.localdate(),
            created_by=self.user,
        )
        result = ActivityService.maintain_activity(
            self.user,
            {
                "log": activity_log,
                "task": self.task,
                "crop": self.crop,
            },
        )
        self.assertTrue(result.success)
        activity = result.data
        self.assertEqual(activity.days_spent, Decimal("0.00"))
        self.assertEqual(activity.cost_total, Decimal("0.0000"))
