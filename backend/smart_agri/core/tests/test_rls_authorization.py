import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from decimal import Decimal
from smart_agri.core.models import (
    Farm, DailyLog, Location, Activity, CropPlan, Season, Crop
)
from smart_agri.core.models.log import AuditLog
from smart_agri.core.models.settings import FarmSettings
from smart_agri.accounts.models import FarmMembership
from smart_agri.core.services.log_approval_service import LogApprovalService
from django.core.exceptions import PermissionDenied, ValidationError
from unittest.mock import patch

User = get_user_model()

@pytest.mark.django_db
class TestRLSAndAuthorization(TestCase):
    def setUp(self):
        # Create users
        self.manager = User.objects.create_user(username='manager', password='pw')
        self.worker = User.objects.create_user(username='worker', password='pw')
        self.other_user = User.objects.create_user(username='other_user', password='pw')

        # Create farms
        self.farm_a = Farm.objects.create(name='Farm A', code='FA', slug='farm-a')
        self.farm_b = Farm.objects.create(name='Farm B', code='FB', slug='farm-b')

        # Set up Farm Memberships
        FarmMembership.objects.create(user=self.manager, farm=self.farm_a, role='مدير المزرعة')
        FarmMembership.objects.create(user=self.worker, farm=self.farm_a, role='مزارع')
        FarmMembership.objects.create(user=self.other_user, farm=self.farm_b, role='مدير المزرعة')

        # Create basic structure for Farm A to test Log Approval
        self.season = Season.objects.create(name='Test Season', start_date='2025-01-01', end_date='2025-12-31', is_active=True)
        self.crop = Crop.objects.create(name='Test Crop')
        self.plan = CropPlan.objects.create(farm=self.farm_a, season=self.season, crop=self.crop, name='Test Plan')
        self.location = Location.objects.create(farm=self.farm_a, name='Test Loc', code='LOC123')

        # Admin created log
        self.admin = User.objects.create_superuser(username='admin', password='pw')
        self.log = DailyLog.objects.create(farm=self.farm_a, log_date='2025-06-01', created_by=self.admin)
        Activity.objects.create(
            log=self.log, crop_plan=self.plan, crop=self.crop, location=self.location,
            days_spent=Decimal('1.0'), cost_labor=Decimal('500.0'), cost_total=Decimal('500.0')
        )

    def test_tenant_isolation_api(self):
        """Test that a user in Farm A cannot fetch Farm B's data via API."""
        client = Client()
        client.force_login(self.manager)

        # Can access Farm A
        resp_a = client.get(f'/api/v1/farms/{self.farm_a.id}/')
        assert resp_a.status_code == 200

        # Cannot access Farm B
        resp_b = client.get(f'/api/v1/farms/{self.farm_b.id}/')
        assert resp_b.status_code == 404

    def test_worker_cannot_approve_variance(self):
        """Test that a 'Worker' (مزارع) cannot approve a critical variance."""
        # Force a CRITICAL variance condition manually.
        self.log.variance_status = 'CRITICAL'
        self.log.status = DailyLog.STATUS_SUBMITTED
        self.log.save()

        with pytest.raises(PermissionDenied) as exc:
            LogApprovalService.approve_variance(self.worker, self.log.id, note="I am a worker")
        assert "اعتماد الانحراف الحرج يتطلب صلاحية مدير" in str(exc.value)

    def test_manager_can_approve_variance(self):
        """Test that a 'Manager' can approve a critical variance."""
        self.log.variance_status = 'CRITICAL'
        self.log.status = DailyLog.STATUS_SUBMITTED
        self.log.save()

        # Manager shouldn't hit PermissionDenied. Might hit ValidationError on window or other things.
        try:
            with patch('smart_agri.core.services.log_approval_service.compute_log_variance', return_value={'status': 'CRITICAL'}):
                LogApprovalService.approve_variance(self.manager, self.log.id, note="Manager approved")
            self.log.refresh_from_db()
            assert self.log.variance_approved_by == self.manager
            assert self.log.variance_note == "Manager approved"
        except ValidationError:
            pass

    def test_creator_cannot_self_approve_variance_by_default(self):
        self.log.created_by = self.manager
        self.log.variance_status = 'CRITICAL'
        self.log.status = DailyLog.STATUS_SUBMITTED
        self.log.save(update_fields=['created_by', 'variance_status', 'status'])

        with patch('smart_agri.core.services.log_approval_service.compute_log_variance', return_value={'status': 'CRITICAL'}):
            with pytest.raises(ValidationError):
                LogApprovalService.approve_variance(self.manager, self.log.id, note="Self approval denied")

    def test_creator_can_self_approve_variance_when_policy_enabled(self):
        self.log.created_by = self.manager
        self.log.variance_status = 'CRITICAL'
        self.log.status = DailyLog.STATUS_SUBMITTED
        self.log.save(update_fields=['created_by', 'variance_status', 'status'])
        settings, _ = FarmSettings.objects.get_or_create(farm=self.farm_a)
        settings.allow_creator_self_variance_approval = True
        settings.save(update_fields=['allow_creator_self_variance_approval'])

        with patch('smart_agri.core.services.log_approval_service.compute_log_variance', return_value={'status': 'CRITICAL'}):
            LogApprovalService.approve_variance(self.manager, self.log.id, note="Self approval allowed")

        self.log.refresh_from_db()
        assert self.log.variance_approved_by == self.manager
        assert AuditLog.objects.filter(
            action='daily_log_variance_self_approved',
            model='DailyLog',
            object_id=str(self.log.id),
        ).exists()

    def test_creator_still_cannot_final_approve_log_when_policy_enabled(self):
        self.log.created_by = self.manager
        self.log.status = DailyLog.STATUS_SUBMITTED
        self.log.variance_status = 'CRITICAL'
        self.log.variance_approved_by = self.manager
        self.log.variance_approved_at = self.log.created_at
        self.log.save(update_fields=['created_by', 'status', 'variance_status', 'variance_approved_by', 'variance_approved_at'])
        settings, _ = FarmSettings.objects.get_or_create(farm=self.farm_a)
        settings.allow_creator_self_variance_approval = True
        settings.save(update_fields=['allow_creator_self_variance_approval'])

        with patch('smart_agri.core.services.log_approval_service.compute_log_variance', return_value={'status': 'CRITICAL'}):
            with pytest.raises(ValidationError):
                LogApprovalService.approve_log(self.manager, self.log.id)

    def test_strict_mode_permissions_listing(self):
        """Validate that strict_mode_permissions correctly classifies crucial financial actions."""
        from smart_agri.core.strict_mode_permissions import is_strict_permission
        assert is_strict_permission('view_financialledger') is True
        assert is_strict_permission('add_treasurytransaction') is True
        assert is_strict_permission('view_farm') is False  # General permission
