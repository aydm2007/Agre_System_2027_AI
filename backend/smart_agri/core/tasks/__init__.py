import logging
import time

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def debug_task(duration=1):
    """
    Agri-Guardian: Verification Task
    Confirms that the worker is picking up tasks from Redis.
    """
    logger.info("Agri-Guardian: Starting Debug Task (Duration: %ss)...", duration)
    time.sleep(duration)
    logger.info("Agri-Guardian: Debug Task Completed.")
    return "Mission Accomplished"


@shared_task
def calculate_cost_async(activity_id, user_id):
    """
    Agri-Guardian: Async Costing Engine.
    Decouples financial math from User UI.
    Chains: Costing -> Finance Sync.
    """
    from smart_agri.core.models.activity import Activity
    from smart_agri.core.services.costing import calculate_activity_cost
    from smart_agri.finance.services.core_finance import FinanceService
    from django.contrib.auth import get_user_model
    from django.core.exceptions import ValidationError
    from django.db import OperationalError

    User = get_user_model()

    try:
        activity = Activity.objects.get(pk=activity_id)
        user = User.objects.get(pk=user_id) if user_id else None

        logger.info("[Async] Calculating cost for Activity %s...", activity_id)
        calculate_activity_cost(activity)

        activity.refresh_from_db()

        if activity.cost_total > 0:
            logger.info("[Async] Syncing Ledger for Activity %s...", activity_id)
            FinanceService.sync_activity_ledger(activity, user)

        logger.info("[Async] Completed Costing & Finance for Activity %s", activity_id)

    except Activity.DoesNotExist:
        logger.warning("[Async] Activity %s not found (Deleted?)", activity_id)
    except (ValidationError, OperationalError, RuntimeError) as e:
        logger.error("[Async] Error processing Activity %s: %s", activity_id, e)

from .integration_tasks import dispatch_integration_outbox_async
