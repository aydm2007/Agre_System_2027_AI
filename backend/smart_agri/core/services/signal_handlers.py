
import logging
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.db import OperationalError
from smart_agri.core.signals import harvest_confirmed, inventory_low_stock, stock_available_for_sale
from smart_agri.core.models.planning import CropPlan
# from smart_agri.sales.services import SalesService (Assume exists or mock)

logger = logging.getLogger(__name__)

@receiver(harvest_confirmed)
def on_harvest_confirmed(sender, activity, quantity, batch_number, user, **kwargs):
    """
    Listener: When Harvest is confirmed -> Notify Sales & Warehousing.
    [Protocol XV] Deep Integration: Call HarvestService to book Asset & Stock.
    """
    logger.info(f"🔔 SIGNAL RECEIVED: Harvest Confirmed {quantity}kg (Batch: {batch_number})")
    
    # 1. Official Inventory & Asset Booking
    try:
        from smart_agri.core.services.harvest_service import HarvestService
        HarvestService.process_harvest(activity, user)
    except (ImportError, ValidationError, OperationalError) as e:
        logger.exception(f"CRITICAL: Failed to process harvest financial impact for {activity.pk}")
        raise e
        # Note: Signals are loosely coupled. If this fails, we might have data inconsistency.
        # Ideally, this call should be DIRECT in ActivityService, but to respect current architecture
        # we keep it here. For strict mode, we log error loudly.

    # 2. Notification (Legacy)
    # [AG-CLEANUP] print(f"   >>> [Integration] Notifying Warehouse: Expect {quantity}kg from {activity.location.name} (Batch {batch_number})")

@receiver(stock_available_for_sale)
def on_stock_available(sender, product_id, quantity, batch_number, **kwargs):
    """
    Listener: When stock is marked for sale.
    """
    logger.info(f"🔔 SIGNAL RECEIVED: Stock Available for Sale {quantity}")
    # [AG-CLEANUP] print(f"   >>> [Integration] Sales Dashboard Updated: +{quantity} units available.")

@receiver(inventory_low_stock)
def on_low_stock(sender, item, current_qty, reorder_level, **kwargs):
    """
    Listener: Low Stock Warning.
    """
    logger.warning(f"🚨 SIGNAL RECEIVED: Low Stock for {item.name} ({current_qty} < {reorder_level})")
    # NotificationService.send_email(PURCHASING_MGR, ...)
    # [AG-CLEANUP] print(f"   >>> [Integration] Email sent to Purchasing: Order more {item.name}!")
@receiver(post_save, sender=CropPlan)
def on_crop_plan_saved(sender, instance, created, **kwargs):
    """
    Listener: When a CropPlan is created/updated.
    Trigger timeline generation if a template is present and it's a new plan.
    """
    if created and instance.template:
        logger.info(f"🔔 SIGNAL RECEIVED: New CropPlan {instance.id} created with template. Generating timeline...")
        try:
             from smart_agri.core.services.planning_timeline_service import PlanningTimelineService
             PlanningTimelineService.generate_timeline_from_template(instance)
        except (ImportError, ValidationError, OperationalError, AttributeError, RuntimeError, ValueError) as e:
             logger.exception(f"Failed to generate timeline for CropPlan {instance.id}: {e}")
