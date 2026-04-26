import logging
from datetime import timedelta
from django.db import transaction
from smart_agri.core.models.planning import CropPlan, PlannedActivity, CropTemplate

logger = logging.getLogger(__name__)

class PlanningTimelineService:
    """
    Service responsible for orchestrating the chronological timeline of a CropPlan.
    Converts Template relative offsets into absolute planned dates.
    """

    @staticmethod
    @transaction.atomic
    def generate_timeline_from_template(crop_plan: CropPlan, template: CropTemplate = None) -> int:
        """
        Materializes PlannedActivity records from a CropTemplate.
        Returns the number of activities created.
        """
        template = template or crop_plan.template
        if not template:
            logger.warning(f"No template found for CropPlan {crop_plan.id}. Skipping timeline generation.")
            return 0

        # Clear existing planned activities to avoid duplicates if re-generating
        # However, we should be careful about manually edited activities.
        # For now, let's just add missing ones or overwrite if instructed.
        
        template_tasks = template.tasks.all()
        created_count = 0
        
        for t_task in template_tasks:
            days_offset = getattr(t_task, 'days_offset', 0)
            duration = getattr(t_task, 'duration_days', 1)
            
            expected_start = crop_plan.start_date + timedelta(days=days_offset)
            expected_end = expected_start + timedelta(days=max(0, duration - 1))
            
            # Use update_or_create to allow idempotent calls
            planned, created = PlannedActivity.objects.update_or_create(
                crop_plan=crop_plan,
                task=t_task.task,
                expected_date_start=expected_start,
                expected_date_end=expected_end,
                defaults={
                    "planned_date": expected_start, # Legacy support
                    "estimated_hours": t_task.estimated_hours,
                    "notes": t_task.notes or f"Generated from template: {template.name}"
                }
            )
            if created:
                created_count += 1
                
        logger.info(f"Generated {created_count} planned activities for CropPlan {crop_plan.id} from template {template.id}")
        return created_count

    @staticmethod
    def shift_plan_dates(crop_plan: CropPlan, days: int):
        """
        Shifts all planned activities in a CropPlan by a specific number of days.
        Used when the whole plan is delayed (e.g. late rain).
        """
        planned_activities = crop_plan.planned_activities.all()
        with transaction.atomic():
            for pa in planned_activities:
                if pa.expected_date_start:
                    pa.expected_date_start += timedelta(days=days)
                if pa.expected_date_end:
                    pa.expected_date_end += timedelta(days=days)
                if pa.planned_date:
                    pa.planned_date += timedelta(days=days)
                pa.save()
        logger.info(f"Shifted {len(planned_activities)} planned activities by {days} days for CropPlan {crop_plan.id}")
