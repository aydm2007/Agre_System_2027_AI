from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver, Signal
from django.db import transaction, OperationalError
from django.db.models import Sum
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError, ObjectDoesNotExist
import logging
from smart_agri.core.models import (
    DailyLog,
    Activity,
    ActivityItem,
    ItemInventory,
    ActivityHarvest,
    StockMovement,
    CropProduct,
    Attachment,
)
from smart_agri.core.services.traceability import TraceabilityService
from smart_agri.core.services.custody_transfer_service import CustodyTransferService
from decimal import Decimal


from smart_agri.core.events import AgriEventBus

logger = logging.getLogger(__name__)

def _delete_file_field(field):
    if not field:
        return
    storage = getattr(field, 'storage', default_storage)
    name = getattr(field, 'name', None)
    if not name:
        return
    try:
        if storage.exists(name):
            storage.delete(name)
    except (OSError, IOError) as exc:
        logger.warning("Failed to delete media file %s: %s", name, exc)

def _cleanup_file_field(instance, field_name):
    field = getattr(instance, field_name, None)
    _delete_file_field(field)

# --- Enterprise Signal Bus (The Nervous System) ---
# [Legacy] Keeping these for backward compatibility during transition
harvest_confirmed = Signal()
inventory_low_stock = Signal()
stock_available_for_sale = Signal()

# [Titan Nebula] New Event Bus Integration
# Note: Receivers should now subscribe via @AgriEventBus.subscribe('event_name')


@receiver(post_delete, sender=Attachment)
def _delete_attachment_file(sender, instance, **kwargs):
    _cleanup_file_field(instance, 'file')


@receiver(pre_save, sender=Attachment)
def _remove_attachment_file_on_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        previous = Attachment.objects.get(pk=instance.pk)
    except Attachment.DoesNotExist:
        return
    new_file = getattr(instance, 'file', None)
    old_file = getattr(previous, 'file', None)
    if old_file and new_file and old_file.name != new_file.name:
        _delete_file_field(old_file)


@receiver(pre_save, sender=Activity)
def assign_batch_number(sender, instance, **kwargs):
    """
    توليد رقم تشغيلة تلقائي عند تسجيل نشاط حصاد.
    """
    is_harvest = False
    if instance.task:
        is_harvest = getattr(instance.task, 'is_harvest_task', False) or 'harvest' in instance.task.name.lower()

    if is_harvest and not getattr(instance, 'batch_number', None):
        farm_code = "UNK"
        loc = None
        if instance.pk:
            first_loc = instance.activity_locations.first()
            loc = first_loc.location if first_loc else None
        if loc and loc.farm:
            farm_code = loc.farm.slug or str(loc.farm.id)
        
        crop_code = "GEN"
        if instance.crop:
            crop_code = getattr(instance.crop, 'code', None) or instance.crop.name[:3]
            
        # استدعاء خدمة التتبع (نحتاج للتأكد من وجود الحقل في الموديل أو تفاصيل الحصاد)
        # ملاحظة: في الهيكل الحالي، batch_number قد يكون في ActivityHarvest
        pass 


@receiver(post_save, sender=DailyLog)
def cascade_soft_delete_daily_log(sender, instance, created, **kwargs):
    """
    FINANCIAL INTEGRITY ENFORCER:
    1. If a DailyLog is soft-deleted (deleted_at set), immediately soft-delete
       all child Activities to prevent them from appearing in financial reports.
    2. When a new DailyLog is created, scan for tree census variances.
    """
    # [AGRI-GUARDIAN] Axis 11: Auto-scan new logs for tree loss detection
    if created:
        try:
            from smart_agri.core.services.loss_prevention import LossPreventionService
            alerts_created = LossPreventionService.analyze_tree_census(instance)
            if alerts_created > 0:
                logger.info(
                    "[AGRI-GUARDIAN §Axis-11] Tree Census scan: %d variance alerts created for DailyLog #%s",
                    alerts_created, instance.pk
                )
        except (ImportError, ValidationError, ObjectDoesNotExist, OperationalError) as e:
            logger.error("[AGRI-GUARDIAN §Axis-11] Tree Census scan failed for DailyLog #%s: %s", instance.pk, e)

    if not created and instance.deleted_at is not None:
        # Fetch alive activities
        activities = instance.activities.filter(deleted_at__isnull=True)
        count = activities.count()
        if count > 0:
            # Bulk soft delete -> REPLACED WITH LOOP
            # FIX: We must call delete() individually to ensure Inventory/Costing reversal logic runs.
            # Using queryset.update() is faster but skips signals/overridden delete methods.
            # Forensic Fix: Use Service to ensure financial/inventory reversal
            # Direct activity.delete() only soft-deletes without reversing ledger/inventory!
            from smart_agri.core.services.activity_service import ActivityService
            from smart_agri.finance.services.core_finance import FinanceService
            for activity in activities:
                 result = ActivityService.delete_activity(user=None, activity=activity)
                 if not result.success:
                     # Legacy/forensic fallback: reverse ledger then soft-delete activity.
                     FinanceService.reverse_activity_ledger(activity, user=None)
                     activity.delete()
                     logger.warning(
                         "Cascade used reversal fallback for Activity %s: %s",
                         activity.id,
                         result.message,
                     )


@receiver(pre_save, sender=DailyLog)
def handle_log_status_change(sender, instance, **kwargs):
    """
    عند تغيّر حالة السجل:
    إذا تحولت الحالة إلى "مرفوض"، يجب إعادة جميع المواد المستخدمة للمخزون.
    """
    if not instance.pk:
        return
    
    try:
        old_instance = DailyLog.objects.get(pk=instance.pk)
    except DailyLog.DoesNotExist:
        return

    # [AUDITOR FIX]: معالجة الرفض وإعادة المخزون
    if instance.status == DailyLog.STATUS_REJECTED and old_instance.status != DailyLog.STATUS_REJECTED:
        with transaction.atomic():
            for activity in instance.activities.filter(deleted_at__isnull=True):
                for item_usage in activity.items.all():
                    # إضافة المخزون المرفوض (+)
                    _adjust_inventory(
                        item_usage.item, 
                        item_usage.uom, 
                        item_usage.qty, 
                        (activity.activity_locations.first().location if activity.activity_locations.exists() else None), 
                        instance.farm
                    )


@receiver(post_save, sender=ActivityItem)
def update_inventory_and_cost(sender, instance, created, **kwargs):
    """
    عند حفظ مادة في النشاط:
    1. خصم الكمية من المخزون (فقط عند الإنشاء لتجنب الخصم المزدوج).
    2. إعادة حساب تكلفة النشاط الأم.
    """
    activity = instance.activity
    
    # 1. تحديث المخزون (Inventory Deduction with Batch Support)
    if created and instance.qty:
        try:
            from smart_agri.inventory.services import InventoryService
            loc = CustodyTransferService.get_consumption_location_for_activity(
                activity=activity,
                item=instance.item,
                required_qty=Decimal(str(instance.qty or 0)),
            )
            InventoryService.record_movement(
                farm=activity.log.farm,
                item=instance.item,
                qty_delta=-(instance.qty),
                location=loc,
                ref_type='activity',
                ref_id=str(activity.id),
                note=f"Activity Item Usage: {activity.pk}",
                batch_number=getattr(instance, 'batch_number', None)
            )
        except (ValidationError, OperationalError, ObjectDoesNotExist) as exc:
            logger.warning("Inventory deduction failed for ActivityItem %s: %s", instance.pk, exc)
            raise

    # 2. تحديث تكلفة النشاط (Roll-up Cost)
    _recalculate_activity_cost(activity)

@receiver(post_delete, sender=ActivityItem)
def return_inventory_and_cost(sender, instance, **kwargs):
    """
    عند حذف مادة:
    1. إعادة الكمية للمخزون (Reverse Logistics).
    2. إعادة حساب تكلفة النشاط.
    """
    # 1. إعادة المخزون (Restocking with Batch Support)
    if instance.item and instance.qty:
        from smart_agri.inventory.services import InventoryService
        try:
            loc = CustodyTransferService.get_consumption_location_for_activity(
                activity=instance.activity,
                item=instance.item,
                required_qty=Decimal("0.000"),
            )
            InventoryService.record_movement(
                farm=instance.activity.log.farm,
                item=instance.item,
                qty_delta=instance.qty,
                location=loc,
                ref_type='activity',
                ref_id=str(instance.activity.id),
                note=f"Activity Item Removal: {instance.activity.pk}",
                batch_number=getattr(instance, 'batch_number', None)
            )
        except (ValidationError, OperationalError, ObjectDoesNotExist) as exc:
            logger.warning("Failed to restore inventory on deletion for %s: %s", instance.pk, exc)
            raise
    
    # 2. تحديث التكلفة
    _recalculate_activity_cost(instance.activity)


@receiver(post_save, sender=ActivityHarvest)
def update_harvest_inventory(sender, instance, created, **kwargs):
    """
    AUTOMATED HARVEST BRIDGE:
    When a harvest is recorded, automatically increase the physical stock
    of the harvested product in the barn/storage location.
    """
    activity = instance.activity
    
    # 0. Safety Check: Only if product is linked to an Item
    if not instance.product_id:
        return

    try:
        product = CropProduct.objects.get(pk=instance.product_id)
        if not product.item: 
            return # No inventory item linked
        item = product.item
    except CropProduct.DoesNotExist:
        return

    # 1. Update Inventory (+)
    if created:
        loc = activity.activity_locations.first().location if activity.activity_locations.exists() else None
        _adjust_inventory(
            item, 
            instance.uom, 
            instance.harvest_quantity, 
            loc, 
            activity.log.farm
        )

        # 2. Traceability (Stock Movement)
        StockMovement.objects.create(
            farm=activity.log.farm,
            item=item,
            location=loc,
            qty_delta=instance.harvest_quantity,
            ref_type='harvest_activity',
            ref_id=str(activity.id),
            note=f"Harvest Log #{activity.log.id}",
            batch_number=instance.batch_number
        )


def _adjust_inventory(item, uom, qty_delta, location, farm):
    """
    دالة مساعدة آمنة لتعديل المخزون مع حماية من التداخل (Transactional Locking)
    """
    if not item or not farm:
        return
    
    try:
        with transaction.atomic():
            # [CRITICAL FIX]: استخدام select_for_update لقفل السجل ومنع تداخل البيانات (Race Conditions)
            inventory, created = ItemInventory.objects.select_for_update().get_or_create(
                item=item,
                farm=farm,
                location=location,
                defaults={'qty': 0, 'uom': uom or item.uom}
            )
            
            # [CRITICAL FIX]: التحقق من وجود رصيد كافٍ قبل الخصم
            if qty_delta < 0 and (inventory.qty + Decimal(str(qty_delta))) < 0:
                raise ValueError(f"⛔ رصيد غير كافٍ للصنف '{item.name}'. المتوفر: {inventory.qty}, المطلوب: {abs(qty_delta)}")

            inventory.qty += Decimal(str(qty_delta))
            inventory.save()
    except ValueError as e:
        # [AUDITOR FIX]: رفع خطأ عدم كفاية المخزون ليراه المستخدم بوضوح
        raise e
    except (ValueError, ValidationError) as e:
        raise e


def _recalculate_activity_cost(activity):
    """
    إعادة حساب التكلفة الإجمالية للنشاط (مواد + عمالة/خدمات).
    DELEGATION: Uses core.services.costing as SSOT.
    """
    from smart_agri.core.services.costing import calculate_activity_cost
    try:
        # Use simple lock=False since we are largely in a signal chain, 
        # though ideally we should be careful about locks.
        # But Costing Service uses update() which is safe.
        calculate_activity_cost(activity, lock=False)
        
    except (ValueError, ValidationError, OperationalError) as e:
        import logging
        logging.getLogger(__name__).warning(f"[AGRI-GUARDIAN] Error calculating cost for Activity {activity.id}: {e}")

@receiver(post_save, sender=Activity)
def recalculate_cost_on_activity_change(sender, instance, created, **kwargs):
    """
    عند تعديل ساعات العمل أو تغيير المقاول، يجب إعادة حساب التكلفة.
    """
    # تجنب التكرار اللانهائي (Recursion) عند حفظ التكلفة
    if kwargs.get('update_fields') and 'cost_total' in kwargs['update_fields']:
        return

    # Keep creation lightweight; cost is recomputed on related mutations or explicit service calls.
    if created:
        return

    _recalculate_activity_cost(instance)


@receiver(post_save, sender=Activity)
def auto_post_solar_depreciation(sender, instance, created, **kwargs):
    """
    [AGRI-GUARDIAN §Axis-9] إهلاك الطاقة الشمسية التلقائي.

    عند إنشاء نشاط يستخدم أصل شمسي مع ساعات تشغيل > 0،
    يتم تسجيل إهلاك تشغيلي تلقائياً في دفتر الأستاذ المالي.

    مثال:
        Activity(asset=لوح_شمسي, machine_hours=8)
        → يحسب الإهلاك لـ 8 ساعات ويسجّل:
          مدين: 7000-DEP-EXP (مصروف إهلاك)
          دائن: 1500-ACC-DEP (إهلاك متراكم)
    """
    if not created:
        return
    # Only process if Activity has a solar asset with operational hours
    asset = instance.asset
    if not asset or getattr(asset, 'category', None) != 'Solar':
        return

    hours = instance.machine_hours
    if not hours or Decimal(str(hours)) <= 0:
        return

    try:
        from smart_agri.core.services.asset_service import AssetService
        user = getattr(instance.log, 'created_by', None) if instance.log else None
        amount = AssetService.post_solar_operational_depreciation(
            asset=asset,
            hours=Decimal(str(hours)),
            user=user,
        )
        if amount > 0:
            logger.info(
                "[AGRI-GUARDIAN §Axis-9] Solar depreciation posted: "
                "Asset=%s, Hours=%s, Amount=%s",
                asset.id, hours, amount,
            )
    except (ImportError, ValidationError, ObjectDoesNotExist, OperationalError) as e:
        logger.error(
            "[AGRI-GUARDIAN §Axis-9] Failed to post solar depreciation "
            "for Activity %s: %s", instance.id, e
        )
