"""
Schedule Variance Service — انحراف الجدول الزمني.

Detects activities completed outside their CropPlan's planned window.
Creates VarianceAlert for out-of-window completions.

AGENTS.md Compliance:
  - Axis 6: Farm-scoped
  - Axis 8: Variance Controls — schedule variance (actual date vs planned window)
  - Axis 7: AuditLog
"""

import logging
from datetime import date as datetype

from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ScheduleVarianceService:
    """
    [AGENTS.md §Variance] Checks if an activity's completion date
    falls outside the CropPlan's planned window (start_date → end_date).
    """

    @staticmethod
    def check_schedule_variance(*, activity, user=None):
        """
        Check if activity's date fits the plan.
        Precision Mode: Checks specific PlannedActivity window if available.
        Legacy Mode: Checks the broad CropPlan window.
        """
        crop_plan = getattr(activity, 'crop_plan', None)
        if not crop_plan:
            return None

        farm = getattr(crop_plan, 'farm', None)
        strict_temporal = getattr(farm.settings, 'enable_timed_plan_compliance', False) if farm and hasattr(farm, 'settings') else False

        # 1. Resolve Target Date Window
        plan_start = crop_plan.start_date
        plan_end = crop_plan.end_date
        target_name = "نافذة الخطة كاملة"

        # Try to find a specific planned activity for this task
        tags = getattr(activity, 'analytical_tags', {}) or {}
        planned_id = tags.get('planned_activity_id')
        
        from smart_agri.core.models.planning import PlannedActivity
        planned_obj = None
        if planned_id:
            planned_obj = PlannedActivity.objects.filter(pk=planned_id).first()
        
        if not planned_obj and strict_temporal:
            # If strict, try to find the earliest uncompleted planned activity for this task
            planned_obj = PlannedActivity.objects.filter(
                crop_plan=crop_plan,
                task=activity.task,
                deleted_at__isnull=True
            ).order_by('expected_date_start').first()

        if planned_obj and (planned_obj.expected_date_start or planned_obj.expected_date_end):
            plan_start = planned_obj.expected_date_start or plan_start
            plan_end = planned_obj.expected_date_end or plan_end
            target_name = f"الموعد المجدد للمهمة ({planned_obj.task.name})"

        # 2. Resolve Actual Activity Date
        activity_date = (
            getattr(activity, 'completed_at', None)
            or getattr(activity, 'activity_date', None)
            or getattr(getattr(activity, 'log', None), 'log_date', None)
        )
        if not activity_date:
            return None

        if hasattr(activity_date, 'date'):
            activity_date = activity_date.date()

        # 3. Validation
        if plan_start <= activity_date <= plan_end:
            return None  # No variance

        # Calculate deviation
        if activity_date < plan_start:
            deviation_days = (plan_start - activity_date).days
            direction = 'EARLY'
        else:
            deviation_days = (activity_date - plan_end).days
            direction = 'LATE'

        # Severity logic
        # For precision mode, intolerance is higher
        if strict_temporal:
            severity = 'WARNING' if deviation_days <= 2 else 'CRITICAL'
        else:
            severity = 'WARNING' if deviation_days <= 14 else 'CRITICAL'

        farm_id = farm.id if farm else getattr(activity, 'farm_id', None)

        # 4. Persistence (VarianceAlert)
        from smart_agri.core.models.report import VarianceAlert
        from decimal import Decimal
        alert = VarianceAlert.objects.create(
            farm_id=farm_id,
            category=VarianceAlert.CATEGORY_SCHEDULE_DEVIATION,
            activity_name=str(getActivityTaskName(activity)),
            planned_cost=Decimal('0.0000'),
            actual_cost=Decimal('0.0000'),
            variance_amount=Decimal(str(deviation_days)),
            variance_percentage=Decimal(str(deviation_days)),
            alert_message=(
                f"🚨 انحراف تخطيطي: النشاط '{getActivityTaskName(activity)}' "
                f"أُنجز بتاريخ {activity_date} "
                f"{'مبكراً' if direction == 'EARLY' else 'متأخراً'} "
                f"عن {target_name} ({plan_start} → {plan_end}) "
                f"بـ {deviation_days} يوم. [{severity}]"
            ),
        )

        # 5. Sector Notification (If Critical)
        if severity == 'CRITICAL' and farm:
            from smart_agri.core.services.notification_service import NotificationService
            NotificationService.notify_sector_finance_director(
                farm=farm,
                message=f"تنبيه حوكمة: انحراف زمني حرج في مزرعة {farm.name}. النشاط {getActivityTaskName(activity)} متأخر بـ {deviation_days} يوم."
            )

        # 6. AuditLog
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='SCHEDULE_VARIANCE',
            model='Activity',
            object_id=str(activity.pk),
            actor=user,
            new_payload={
                'direction': direction,
                'deviation_days': deviation_days,
                'severity': severity,
                'target': target_name,
                'window': f"{plan_start} → {plan_end}",
            },
        )

        return {
            "has_variance": True,
            "direction": direction,
            "deviation_days": deviation_days,
            "severity": severity,
            "target": target_name,
        }

def getActivityTaskName(activity):
    return getattr(activity.task, 'name', None) or getattr(activity, 'task_type', None) or f"Activity #{activity.pk}"
