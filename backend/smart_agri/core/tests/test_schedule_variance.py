"""
[AGRI-GUARDIAN] Tests for ScheduleVarianceService.

Covers:
  - Axis 8: Variance Controls (schedule deviation)
  - Axis 6: Farm-scoped
  - Axis 7: AuditLog creation
  - Axis 14: Schedule Variance (activity window check + VarianceAlert)
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch


class TestScheduleVarianceService:
    """Tests for ScheduleVarianceService.check_schedule_variance"""

    def _make_activity(self, activity_date, plan_start, plan_end, farm_id=1):
        """Create a mock activity with crop_plan having a date window."""
        activity = MagicMock()
        activity.pk = 42
        activity.farm_id = farm_id
        activity.completed_at = None
        activity.activity_date = activity_date
        activity.task_type = 'IRRIGATION'
        activity.log = MagicMock()
        activity.log.farm_id = farm_id
        activity.log.log_date = activity_date

        crop_plan = MagicMock()
        crop_plan.start_date = plan_start
        crop_plan.end_date = plan_end
        activity.crop_plan = crop_plan

        return activity

    def test_no_variance_within_window(self):
        """Activity within plan window → no variance."""
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService

        activity = self._make_activity(
            date(2026, 6, 15), date(2026, 6, 1), date(2026, 6, 30)
        )
        result = ScheduleVarianceService.check_schedule_variance(activity=activity)
        assert result is None

    def test_no_variance_without_crop_plan(self):
        """No crop_plan → skip (nothing to compare)."""
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService

        activity = MagicMock()
        activity.crop_plan = None
        result = ScheduleVarianceService.check_schedule_variance(activity=activity)
        assert result is None

    def test_no_variance_without_plan_dates(self):
        """Crop plan without start_date or end_date → skip."""
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService

        activity = MagicMock()
        activity.crop_plan = MagicMock()
        activity.crop_plan.start_date = None
        activity.crop_plan.end_date = None
        result = ScheduleVarianceService.check_schedule_variance(activity=activity)
        assert result is None

    @patch('smart_agri.core.services.schedule_variance_service.AuditLog', create=True)
    @patch('smart_agri.core.services.schedule_variance_service.VarianceAlert', create=True)
    def test_late_activity_detected(self, MockAlert, MockAudit):
        """[Axis 14] Activity after plan end → LATE variance."""
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService

        MockAlert.CATEGORY_SCHEDULE_DEVIATION = 'SCHEDULE_DEVIATION'
        activity = self._make_activity(
            date(2026, 7, 10), date(2026, 6, 1), date(2026, 6, 30)
        )
        result = ScheduleVarianceService.check_schedule_variance(activity=activity)

        assert result is not None
        assert result["has_variance"] is True
        assert result["direction"] == "LATE"
        assert result["deviation_days"] == 10

    @patch('smart_agri.core.services.schedule_variance_service.AuditLog', create=True)
    @patch('smart_agri.core.services.schedule_variance_service.VarianceAlert', create=True)
    def test_early_activity_detected(self, MockAlert, MockAudit):
        """[Axis 14] Activity before plan start → EARLY variance."""
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService

        MockAlert.CATEGORY_SCHEDULE_DEVIATION = 'SCHEDULE_DEVIATION'
        activity = self._make_activity(
            date(2026, 5, 25), date(2026, 6, 1), date(2026, 6, 30)
        )
        result = ScheduleVarianceService.check_schedule_variance(activity=activity)

        assert result is not None
        assert result["direction"] == "EARLY"
        assert result["deviation_days"] == 7

    @patch('smart_agri.core.services.schedule_variance_service.AuditLog', create=True)
    @patch('smart_agri.core.services.schedule_variance_service.VarianceAlert', create=True)
    def test_severity_warning_under_14_days(self, MockAlert, MockAudit):
        """[Axis 14] ≤14 days deviation → WARNING severity."""
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService

        MockAlert.CATEGORY_SCHEDULE_DEVIATION = 'SCHEDULE_DEVIATION'
        activity = self._make_activity(
            date(2026, 7, 5), date(2026, 6, 1), date(2026, 6, 30)
        )
        result = ScheduleVarianceService.check_schedule_variance(activity=activity)

        assert result["severity"] == "WARNING"
        assert result["deviation_days"] == 5

    @patch('smart_agri.core.services.schedule_variance_service.AuditLog', create=True)
    @patch('smart_agri.core.services.schedule_variance_service.VarianceAlert', create=True)
    def test_severity_critical_over_14_days(self, MockAlert, MockAudit):
        """[Axis 14] >14 days deviation → CRITICAL severity."""
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService

        MockAlert.CATEGORY_SCHEDULE_DEVIATION = 'SCHEDULE_DEVIATION'
        activity = self._make_activity(
            date(2026, 8, 1), date(2026, 6, 1), date(2026, 6, 30)
        )
        result = ScheduleVarianceService.check_schedule_variance(activity=activity)

        assert result["severity"] == "CRITICAL"
        assert result["deviation_days"] == 32

    def test_service_does_not_use_float(self):
        """[Axis 5] The service must not use float()."""
        import inspect
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService
        source = inspect.getsource(ScheduleVarianceService)
        assert 'float(' not in source, "ScheduleVarianceService must not use float()"

    def test_service_creates_variance_alert(self):
        """[Axis 8] Variance detected must result in VarianceAlert creation."""
        import inspect
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService
        source = inspect.getsource(ScheduleVarianceService)
        assert 'VarianceAlert.objects.create' in source, \
            "Must create VarianceAlert for schedule deviations"

    def test_service_creates_audit_log(self):
        """[Axis 7] The service must create AuditLog entries."""
        import inspect
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService
        source = inspect.getsource(ScheduleVarianceService)
        assert 'AuditLog.objects.create' in source, \
            "Must create AuditLog for schedule variance"

    @patch('smart_agri.core.services.schedule_variance_service.AuditLog', create=True)
    @patch('smart_agri.core.services.schedule_variance_service.VarianceAlert', create=True)
    def test_boundary_date_on_plan_end_no_variance(self, MockAlert, MockAudit):
        """Activity exactly on plan end date → no variance."""
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService

        activity = self._make_activity(
            date(2026, 6, 30), date(2026, 6, 1), date(2026, 6, 30)
        )
        result = ScheduleVarianceService.check_schedule_variance(activity=activity)
        assert result is None

    @patch('smart_agri.core.services.schedule_variance_service.AuditLog', create=True)
    @patch('smart_agri.core.services.schedule_variance_service.VarianceAlert', create=True)
    def test_boundary_date_on_plan_start_no_variance(self, MockAlert, MockAudit):
        """Activity exactly on plan start date → no variance."""
        from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService

        activity = self._make_activity(
            date(2026, 6, 1), date(2026, 6, 1), date(2026, 6, 30)
        )
        result = ScheduleVarianceService.check_schedule_variance(activity=activity)
        assert result is None
