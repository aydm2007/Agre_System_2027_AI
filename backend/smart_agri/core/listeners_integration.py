from __future__ import annotations

from smart_agri.core.models import Activity
from smart_agri.integration_hub.event_contracts import ActivityLogged
from smart_agri.integration_hub.persistence import publish_event_after_commit


def publish_activity_committed_to_outbox(sender=None, **kwargs):
    activity_id = kwargs.get('activity_id')
    user_id = kwargs.get('user_id')
    if not activity_id:
        return
    activity = (
        Activity.objects.select_related('log', 'task', 'crop', 'asset')
        .filter(pk=activity_id)
        .first()
    )
    if activity is None:
        return
    farm_id = getattr(activity.log, 'farm_id', None)
    event = ActivityLogged(
        aggregate_id=str(activity.id),
        activity_type=getattr(activity.task, 'name', None) or 'activity',
        quantity=str(activity.days_spent or 0),
        farm_id=str(farm_id) if farm_id else None,
        payload={
            'cost_total': str(activity.cost_total or 0),
            'crop_id': activity.crop_id,
            'task_id': activity.task_id,
            'asset_id': activity.asset_id,
            'log_id': activity.log_id,
        },
        metadata={'source': 'activity_committed_signal'},
    )
    publish_event_after_commit(
        event,
        destination='activity-events',
        farm_id=farm_id,
        activity_id=activity.id,
        created_by_id=user_id,
    )
