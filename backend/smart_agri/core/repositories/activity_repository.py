from django.db import transaction
from django.core.exceptions import ValidationError
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.log import DailyLog
from smart_agri.core.constants import DailyLogStatus

class ActivityRepository:
    """
    Repository for Activity Aggregate.
    Abstracts persistence details (ORM, Locking, Validation triggers).
    """

    def get_by_id(self, activity_id: int, for_update: bool = False) -> Activity:
        qs = Activity.objects.all()
        if for_update:
            qs = qs.select_for_update()
        return qs.get(pk=activity_id)

    def create(self, data: dict, user=None) -> Activity:
        """Creates an activity instance but does not save it (Stage 1)."""
        activity = Activity(**data)
        if user:
            activity.created_by = user
            activity.updated_by = user
        return activity
    
    def update(self, activity: Activity, data: dict, user=None) -> Activity:
        """Updates attributes."""
        for key, value in data.items():
            setattr(activity, key, value)
        if user:
            activity.updated_by = user
        return activity

    def validate_log_status_for_insert(self, log_id: int):
        """Ensures we don't insert into locked logs."""
        log = DailyLog.objects.select_for_update().get(pk=log_id)
        if log.status in [DailyLogStatus.APPROVED, DailyLogStatus.SUBMITTED]:
             raise ValidationError(f"لا يمكن إضافة أنشطة إلى سجل في حالة {log.status}.")
        return log

    def save(self, activity: Activity):
        """Persists the activity with full validation."""
        activity.full_clean()
        activity.save()
        return activity

    def delete(self, activity: Activity):
        activity.delete()
