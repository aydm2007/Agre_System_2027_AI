from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from smart_agri.core.models import DailyLog, Activity, Farm
from smart_agri.core.services.log_approval_service import LogApprovalService
from smart_agri.core.models.settings import Supervisor
from decimal import Decimal

class StrictLogClosingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='worker')
        self.approver = User.objects.create_user(username='boss')
        self.farm = Farm.objects.create(name="Test Farm", total_area=100)
        self.supervisor = Supervisor.objects.create(user=self.approver, farm=self.farm)
        self.log = DailyLog.objects.create(
            farm=self.farm, 
            log_date="2024-01-01", 
            created_by=self.user,
            status=DailyLog.STATUS_SUBMITTED
        )

    def test_approve_log_ghost_cost_blocked(self):
        """Test that approving a log with Zero Cost but Hours raises ValidationError."""
        # Create an activity with Hours but NO Cost (simulate missing LaborRate)
        Activity.objects.create(
            log=self.log,
            days_spent=Decimal("5.00"),
            cost_total=Decimal("0.00"), # Zero Cost
            created_by=self.user
        )
        
        with self.assertRaisesMessage(ValidationError, "ولكن التكلفة صفر"):
            LogApprovalService.approve_log(self.approver, self.log.pk)

    def test_approve_log_success(self):
        """Test success path with valid cost."""
        Activity.objects.create(
            log=self.log,
            days_spent=Decimal("5.00"),
            cost_total=Decimal("100.00"), # Valid Cost
            created_by=self.user
        )
        
        log = LogApprovalService.approve_log(self.approver, self.log.pk)
        self.assertEqual(log.status, DailyLog.STATUS_APPROVED)
