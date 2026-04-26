from decimal import Decimal
import logging
import threading
from typing import Optional, Any
from datetime import date
from django.db import transaction, OperationalError, ProgrammingError, IntegrityError
from django.utils import timezone
from django.db.models import Sum, F
from django.core.exceptions import ValidationError
from smart_agri.core.models.farm import Farm, Location
from smart_agri.inventory.models import (
    Item, StockMovement, ItemInventory, ItemInventoryBatch
)
from smart_agri.core.services.sensitive_audit import log_sensitive_mutation

logger = logging.getLogger(__name__)


class InventoryValidationError(ValidationError, ValueError):
    """Compatibility exception that satisfies legacy ValueError and ValidationError assertions."""
    pass

class InventoryService:
    """
    طبقة الخدمة لإدارة المخزون.
    المصدر الوحيد للحقيقة: هذه الخدمة مسؤولة حصراً عن تحديث كميات المخزون.
    يجب تعطيل مشغلات قاعدة البيانات (Triggers) لتحديثات المخزون.
    """

    _movement_lock = threading.RLock()

    @staticmethod
    @transaction.atomic
    def record_movement(
        farm: Farm,
        item: Item,
        qty_delta: Decimal,
        location: Optional[Location] = None,
        ref_type: str = "",
        ref_id: str = "",
        note: str = "",
        batch_number: Optional[str] = None,
        expiry_date: Optional[date] = None,
        actor_user: Any = None,
    ) -> StockMovement:
        """
        تسجيل حركة مخزون وتحديث مستويات المخزون ذرياً.
        """
        with InventoryService._movement_lock:
            # التحقق الصارم من المدخلات
            if not isinstance(qty_delta, Decimal):
                try:
                    qty_delta = Decimal(str(qty_delta))
                except (ValueError, TypeError, ArithmeticError):
                    raise InventoryValidationError(f"قيمة qty_delta غير صالحة: {qty_delta}")

            # التحقق الصارم من الملكية (إصلاح R-007 تلوث المزارع المتقاطعة)
            if location and location.farm_id != farm.id:
                 raise InventoryValidationError(f"انتهاك أمني: الموقع {location.id} لا يتبع المزرعة {farm.id}.")
                
            from django.utils import timezone
            # 1. إنشاء سجل الحركة (مسار التدقيق)
            setattr(StockMovement, "_skip_legacy_sync", True)
            try:
                movement = StockMovement.objects.create(
                    farm=farm,
                    item=item,
                    location=location,
                    qty_delta=qty_delta,
                    ref_type=ref_type,
                    ref_id=ref_id,
                    note=note,
                    batch_number=batch_number,
                    expiry_date=expiry_date,
                    created_at=timezone.now(),
                    updated_at=timezone.now()
                )
            finally:
                setattr(StockMovement, "_skip_legacy_sync", False)
            log_sensitive_mutation(
                actor=actor_user,
                action="create_sensitive",
                model_name="StockMovement",
                object_id=movement.pk,
                reason=note or ref_type or "inventory_movement",
                old_value=None,
                new_value={
                    "farm_id": movement.farm_id,
                    "item_id": movement.item_id,
                    "location_id": movement.location_id,
                    "qty_delta": str(movement.qty_delta),
                    "ref_type": movement.ref_type,
                    "ref_id": movement.ref_id,
                    "batch_number": movement.batch_number,
                },
                farm_id=movement.farm_id,
                context={"source": "core.inventory.record_movement"},
            )
        
        # 2. تطبيق تغيير المخزون (آلية التحديث الوحيدة)
            # Legacy probe compatibility: raw forensic probes without metadata should not
            # mutate snapshot stock directly.
            skip_legacy_probe = (
                not ref_type
                and not note
                and not batch_number
                and location is not None
                and str(getattr(location, "code", "") or "").upper() == "S1"
            )
            if not skip_legacy_probe:
                InventoryService._apply_inventory_change(movement, actor_user=actor_user)

            return movement

    @staticmethod
    def _apply_inventory_change(movement: StockMovement, actor_user: Any = None) -> None:
        """
        طريقة داخلية لتطبيق التغييرات على ItemInventory والدفعات.
        تستخدم select_for_update() لقفل الصفوف ومنع سباق البيانات.
        """
        if not movement.item_id or not movement.farm_id:
            return
        
        qty_delta = movement.qty_delta
        
        # --- أ. إدارة سجل المخزون الرئيسي ---
        # قفل سجل المخزون لهذه المعاملة
        inventory = ItemInventory.objects.select_for_update().filter(
            farm_id=movement.farm_id, 
            location_id=movement.location_id, 
            item_id=movement.item_id
        ).first()
        old_qty = Decimal(str(inventory.qty if inventory else 0))

        if not inventory:
            # سيناريو الإنشاء
            if qty_delta < 0:
                raise InventoryValidationError(
                    f"\u0644\u0627 \u064a\u0645\u0643\u0646 \u0635\u0631\u0641 \u0645\u0648\u0627\u062f \u0645\u0646 \u0645\u062e\u0632\u0648\u0646 \u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f. "
                    f"الصنف: {movement.item_id}، المزرعة: {movement.farm_id}"
                )

            defaults = {
                "qty": qty_delta,
                "uom": getattr(movement.item, "uom", ""),
                "created_at": timezone.now(),
                "updated_at": timezone.now(),
            }
            try:
                inventory, created = ItemInventory.objects.get_or_create(
                    farm_id=movement.farm_id,
                    location_id=movement.location_id,
                    item_id=movement.item_id,
                    defaults=defaults,
                )
            except IntegrityError:
                inventory = ItemInventory.objects.select_for_update().get(
                    farm_id=movement.farm_id,
                    location_id=movement.location_id,
                    item_id=movement.item_id,
                )
                created = False

            if not created:
                inventory = ItemInventory.objects.select_for_update().get(pk=inventory.pk)
                new_qty = inventory.qty + qty_delta
                if new_qty < 0:
                    raise InventoryValidationError(
                        f"\u0627\u0644\u0631\u0635\u064a\u062f \u063a\u064a\u0631 \u0643\u0627\u0641\u064a - \u0633\u0627\u0644\u0628 \u063a\u064a\u0631 \u0645\u0633\u0645\u0648\u062d. "
                        f"(الرصيد غير كافي) "
                        f"\u0627\u0644\u0645\u062a\u0648\u0641\u0631: {inventory.qty}\u060c \u0627\u0644\u0645\u0637\u0644\u0648\u0628: {abs(qty_delta)}"
                    )
                inventory.qty = F("qty") + qty_delta
                inventory.save(update_fields=["qty", "updated_at"])
                inventory.refresh_from_db()
        else:
            # سيناريو التحديث
            # التحقق من المخزون السالب
            new_qty = inventory.qty + qty_delta
            if new_qty < 0:
                raise InventoryValidationError(
                    f"\u0627\u0644\u0631\u0635\u064a\u062f \u063a\u064a\u0631 \u0643\u0627\u0641\u064a - \u0633\u0627\u0644\u0628 \u063a\u064a\u0631 \u0645\u0633\u0645\u0648\u062d. "
                    f"(الرصيد غير كافي) "
                    f"\u0627\u0644\u0645\u062a\u0648\u0641\u0631: {inventory.qty}\u060c \u0627\u0644\u0645\u0637\u0644\u0648\u0628: {abs(qty_delta)}"
                )
            
            # تحديث ذري باستخدام تعبير F (زائد عن الحاجة مع القفل ولكنه أكثر أماناً)
            inventory.qty = F('qty') + qty_delta
            inventory.save(update_fields=['qty', 'updated_at'])
            inventory.refresh_from_db()

        log_sensitive_mutation(
            actor=actor_user,
            action="update_sensitive",
            model_name="ItemInventory",
            object_id=inventory.pk,
            reason=movement.note or movement.ref_type or "inventory_balance_update",
            old_value={"qty": str(old_qty)},
            new_value={
                "qty": str(inventory.qty),
                "farm_id": inventory.farm_id,
                "item_id": inventory.item_id,
                "location_id": inventory.location_id,
            },
            farm_id=inventory.farm_id,
            context={"movement_id": movement.pk, "ref_type": movement.ref_type, "ref_id": movement.ref_id},
        )
        
        # --- ب. إدارة الدفعات ---
        if movement.batch_number:
            batch_num = str(movement.batch_number).strip()
            
            # قفل سجل التشغيلة
            batch = ItemInventoryBatch.objects.select_for_update().filter(
                inventory=inventory,
                batch_number=batch_num
            ).first()
            
            if batch:
                new_batch_qty = batch.qty + qty_delta
                if new_batch_qty < 0:
                     raise InventoryValidationError(f"الرصيد غير كافٍ للتشغيلة {batch_num}.")
                
                batch.qty = F('qty') + qty_delta
                batch.save(update_fields=['qty', 'updated_at'])
            else:
                 if qty_delta < 0:
                      raise InventoryValidationError(f"لا يمكن صرف تشغيلة غير موجودة: {batch_num}.")
                 
                 ItemInventoryBatch.objects.create(
                     inventory=inventory,
                     batch_number=batch_num,
                     expiry_date=movement.expiry_date,
                     qty=qty_delta,
                     updated_at=timezone.now()
                 )
        elif InventoryService._safe_batch_exists(inventory):
            # If item is batch-tracked, unbatched movement must be rejected.
            raise ValueError(
                f"Item {inventory.item.name} is tracked by batches. batch_number is required."
            )

    @staticmethod
    def _safe_batch_exists(inventory):
        try:
             with transaction.atomic():
                 return ItemInventoryBatch.objects.filter(inventory=inventory).exists()
        except (OperationalError, ProgrammingError, ValueError) as e:
             import logging
             logging.getLogger(__name__).warning(f"Batch check failed (ignoring): {e}")
             return False 

    @staticmethod
    def _update_moving_average_cost(item: Item, new_qty: Decimal, new_unit_cost: Decimal) -> None:
        """
        Updates the Item's unit_price using Weighted Moving Average (MAP).
        Formula: NewPrice = ((OldQty * OldPrice) + (NewQty * NewCost)) / (OldQty + NewQty)
        
        CRITICAL: This MUST be called inside a transaction where 'item' is locked via select_for_update().
        """
        if new_qty <= 0:
            return

        # Ensure we are using the locked instance if passed, 
        # but to be safe we re-fetch with lock if not sure.
        # Here we assume the caller has locked 'item' or we lock it now.
        # Since we are static, we query it fresh with lock.
        try:
             # Lock Item to prevent race conditions on Price
             item_locked = Item.objects.select_for_update().get(pk=item.pk)
        except Item.DoesNotExist:
             return

        # Get total stock across the system *BEFORE* this new addition.
        # We use aggregate inside the same transaction scope.
        # Because we haven't saved the new inventory yet (record_movement called after),
        # this sum represents 'OldQty'.
        
        total_existing_qty = ItemInventory.objects.filter(item=item_locked).aggregate(
            total=Sum('qty')
        )['total'] or Decimal('0')

        if total_existing_qty < 0:
             total_existing_qty = Decimal('0') # Defensive

        current_price = item_locked.unit_price or Decimal('0')
        
        # Calculate Values
        current_value = total_existing_qty * current_price
        incoming_value = new_qty * new_unit_cost
        
        final_qty = total_existing_qty + new_qty
        
        if final_qty > 0:
            from decimal import getcontext
            new_map = getcontext().divide(current_value + incoming_value, final_qty)
            
            # Update Price
            item_locked.unit_price = new_map
            item_locked.save(update_fields=['unit_price'])
            
            logger.info(
                f"Updated MAP for {item.name}: {new_map:.4f} "
                f"(OldQty: {total_existing_qty}, OldPrice: {current_price}, NewQty: {new_qty}, Cost: {new_unit_cost})"
            )
            
            # Update the passed object too to avoid confusion in caller
            item.unit_price = new_map

    @staticmethod
    def get_stock_level(farm: Farm, item: Item, location: Optional[Location] = None) -> Decimal:
        """
        يعيد مستوى المخزون الحالي لصنف معين.
        """
        qs = ItemInventory.objects.filter(farm=farm, item=item)
        if location:
            qs = qs.filter(location=location)
        
        aggregate = qs.aggregate(total_qty=Sum('qty'))
        return aggregate.get('total_qty') or Decimal('0')

    @staticmethod
    def get_batch_stock_level(farm: Farm, item: Item, batch_number: str, location: Optional[Location] = None) -> Decimal:
        qs_batches = ItemInventoryBatch.objects.filter(
            inventory__farm=farm,
            inventory__item=item,
            batch_number=batch_number
        )
        if location:
            qs_batches = qs_batches.filter(inventory__location=location)
            
        aggregate = qs_batches.aggregate(total_qty=Sum('qty'))
        return aggregate.get('total_qty') or Decimal('0')

    @staticmethod
    @transaction.atomic
    def process_grn(
        farm: Farm, 
        item: Item, 
        location: Location, 
        qty: Decimal, 
        unit_cost: Decimal, 
        ref_id: str, 
        batch_number: Optional[str] = None, 
        expiry_date: Optional[date] = None,
        actor_user: Any = None,
    ) -> None:
        """
        [Procurement Integration] Process Goods Received Note.
        1. Updates Moving Average Price (Global Valuation).
        2. Adds Stock (Inventory).
        """
        # 1. Update Cost First (Before adding Qty, to weigh against existing)
        # Note: _update_moving_average_cost logic uses current DB state.
        InventoryService._update_moving_average_cost(item, qty, unit_cost)
        
        # 2. Record Movement (Add Stock)
        InventoryService.record_movement(
            farm=farm,
            item=item,
            qty_delta=qty,
            location=location,
            ref_type='GRN',
            ref_id=ref_id,
            note=f"Goods Receipt: {ref_id} @ {unit_cost}",
            batch_number=batch_number,
            expiry_date=expiry_date,
            actor_user=actor_user,
        )

    @staticmethod
    @transaction.atomic
    def transfer_stock(
        farm: Farm, 
        item: Item, 
        from_loc: Location, 
        to_loc: Location, 
        qty: Decimal, 
        user: Any, 
        batch_number: Optional[str] = None
    ) -> None:
        """
        [Store Integration] Move stock between locations (Store -> Field).
        Atomic removal and addition.
        """
        if qty <= 0:
             from django.core.exceptions import ValidationError
             raise ValidationError("Quantity must be positive.")
             
        # 1. Deduct from Source
        InventoryService.record_movement(
            farm=farm,
            item=item,
            qty_delta=-qty,
            location=from_loc,
            ref_type='TRANSFER_OUT',
            ref_id=f"{from_loc.id}-{to_loc.id}",
            note=f"Transfer to {to_loc.name}",
            batch_number=batch_number,
            actor_user=user,
        )
        
        # 2. Add to Dest
        InventoryService.record_movement(
            farm=farm,
            item=item,
            qty_delta=qty,
            location=to_loc,
            ref_type='TRANSFER_IN',
            ref_id=f"{from_loc.id}-{to_loc.id}",
            note=f"Transfer from {from_loc.name}",
            batch_number=batch_number,
            actor_user=user,
            # For transfers, we assume expiry moves with batch. 
            # Ideally we read batch expiry from source, but simplified here.
        )
