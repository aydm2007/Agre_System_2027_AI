import logging
from .events import ActivityCreated, ActivityUpdated, ActivityDeleted
from smart_agri.core.services.tree_inventory import TreeInventoryService
from smart_agri.finance.services.core_finance import FinanceService

logger = logging.getLogger(__name__)

def handle_finance_sync(event):
    """
    Listens to Activity changes and syncs Ledger.
    [IDEMPOTENCY VERIFIED]: FinanceService.sync_activity_ledger uses 'delta' logic.
    Reprocessing the same event will result in delta=0, creating no side-effects.
    """
    activity = event.activity
    user = event.user
    
    # Financial Sync Logic (Extracted from Service)
    if activity.cost_total and activity.cost_total > 0:
        logger.info(f"Listener: Syncing Ledger for Activity {activity.pk}")
        FinanceService.sync_activity_ledger(activity, user)

def handle_finance_reversal(event):
    """
    Listens to Activity deletion and reverses Ledger.
    [IDEMPOTENCY VERIFIED]: Checks for existence of active Ledger entries before reversing.
    """
    activity = event.activity
    user = event.user
    logger.info(f"Listener: Reversing Ledger for Activity {activity.pk}")
    FinanceService.reverse_activity_ledger(activity, user)

def handle_inventory_sync(event):
    """
    Listens to Activity changes and syncs Tree Inventory.
    [IDEMPOTENCY VERIFIED]: TreeInventoryService uses 'upsert' on TreeStockEvent.
    Identical events will simply update the existing Record without duplication.
    """
    activity = event.activity
    user = event.user
    
    if TreeInventoryService.determine_event_type(activity):
        logger.info(f"Listener: Syncing Inventory for Activity {activity.pk}")
        TreeInventoryService.record_event_from_activity(activity, user=user)

def handle_inventory_reversal(event):
    """
    Listens to Activity deletion and reverses Inventory.
    [IDEMPOTENCY VERIFIED]: Checks for existence of TreeStockEvent before deleting.
    """
    activity = event.activity
    user = event.user
    TreeInventoryService.reverse_activity(activity=activity, user=user)

def handle_costing_async(event):
    """
    Listens to Activity Committed events and triggers Async Costing Task.
    Decouples strict costing math from the HTTP Request.
    """
    from smart_agri.core.tasks import calculate_cost_async
    
    activity = event.activity
    user = event.user
    
    # Trigger Celery Task
    # on_commit ensures we don't fire task before DB transaction commits
    from django.db import transaction
    
    logger.info(f"Listener: Dispatching Async Costing for Activity {activity.pk}")
    transaction.on_commit(
        lambda: calculate_cost_async.delay(activity.id, user.id if user else None)
    )

# HR Sync would go here too
# def handle_hr_sync(event): ...
