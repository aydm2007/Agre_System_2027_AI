from decimal import Decimal
import logging
from django.db import transaction
from django.db.models import Sum, F
from django.core.exceptions import ValidationError
from django.utils import timezone

# DEPENDENCY IMPORTS (Core)
from smart_agri.core.models.farm import Farm, Location

# LOCAL IMPORTS (Inventory)
from smart_agri.inventory.models import (
    Item, StockMovement, ItemInventory, ItemInventoryBatch,
    PurchaseOrder, PurchaseOrderItem
)
from smart_agri.core.services.sensitive_audit import log_sensitive_mutation
from smart_agri.core.services.forensic_service import ForensicService

logger = logging.getLogger(__name__)

class InventoryService:
    """
    طبقة الخدمة لإدارة المخزون (App: smart_agri.inventory).
    """

    @staticmethod
    @transaction.atomic
    def record_movement(
        farm: Farm,
        item: Item,
        qty_delta: Decimal,
        location: Location = None,
        ref_type: str = "",
        ref_id: str = "",
        note: str = "",
        batch_number: str = None,
        expiry_date = None,
        date = None, # Add explicit date parameter
        actor_user = None,
    ) -> StockMovement:
        """
        تسجيل حركة مخزون وتحديث مستويات المخزون ذرياً.
        """
        # [AGRI-GUARDIAN] FISCAL COMPLIANCE
        # يجب التحقق من أن تاريخ الحركة يقع ضمن فترة مالية مفتوحة.
        movement_date = date or timezone.now().date()
        from smart_agri.finance.services.core_finance import FinanceService
        FinanceService.check_fiscal_period(movement_date, farm, strict=True)

        # التحقق الصارم من المدخلات
        if not isinstance(qty_delta, Decimal):
            raise ValidationError(
                "القيم العشرية من النوع float مرفوضة في مسارات المخزون. استعمل Decimal(19, 4)."
            )

        qty_delta = qty_delta.quantize(Decimal('0.0001'))

        # التحقق الصارم من الملكية
        if location and location.farm_id != farm.id:
             raise ValidationError(f"انتهاك أمني: الموقع {location.id} لا ينتمي إلى المزرعة {farm.id}.")
                
        # 1. إنشاء سجل الحركة
        movement = StockMovement.objects.create(
            farm=farm,
            item=item,
            location=location,
            qty_delta=qty_delta,
            ref_type=ref_type,
            ref_id=ref_id,
            note=note,
            batch_number=batch_number,
            expiry_date=expiry_date
            # Assuming model has a date field, usually auto_now_add but ideally explicit for backdating
        )
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
            context={"source": "inventory.record_movement"},
        )
        
        # [AXIS 20] Forensic Commitment
        proof = ForensicService.sign_transaction(
            agent=str(getattr(actor_user, 'username', 'SYSTEM')),
            action='INVENTORY_MOVEMENT',
            payload={
                'item': item.name,
                'delta': str(qty_delta),
                'ref': ref_id
            }
        )
        # Store in metadata/audit log if available, or just log
        logger.info(f"Forensic Proof Committed: {proof['event_id']}")
        
        # 2. تطبيق تغيير المخزون
        InventoryService._apply_inventory_change(movement, actor_user=actor_user)
        
        return movement

    @staticmethod
    def _apply_inventory_change(movement: StockMovement, actor_user=None):
        if not movement.item_id or not movement.farm_id:
            return
        
        qty_delta = movement.qty_delta
        
        # --- [AGRI-GUARDIAN] Axis-6: Tenant Isolation Safety Gate ---
        # Ensure we are not updating inventory for a different farm via movement leakage.
        
        # --- أ. إدارة سجل المخزون الرئيسي ---
        # استخدام select_for_update لقفل السجل ومنع التضارب
        inventory = ItemInventory.objects.select_for_update().filter(
            farm_id=movement.farm_id, 
            location_id=movement.location_id, 
            item_id=movement.item_id
        ).first()
        old_qty = Decimal(str(inventory.qty if inventory else 0))

        if not inventory:
            if qty_delta < 0:
                raise ValidationError(
                    f"لا يمكن صرف مواد من مخزون غير موجود. "
                    f"الصنف: {movement.item_id}، المزرعة: {movement.farm_id}"
                )
            
            uom_val = getattr(movement.item, 'uom', '')
            # Use get_or_create to handle race condition
            inventory, created = ItemInventory.objects.get_or_create(
                farm_id=movement.farm_id,
                location_id=movement.location_id,
                item_id=movement.item_id,
                defaults={'qty': 0, 'uom': uom_val}
            )
            if not created:
                inventory = ItemInventory.objects.select_for_update().get(pk=inventory.pk)

            inventory.qty = F('qty') + qty_delta
            inventory.save(update_fields=['qty', 'updated_at'])
            inventory.refresh_from_db()
        else:
            if inventory.farm_id != movement.farm_id:
                raise ValidationError(
                    f"SECURITY [Axis-6]: Tenant Isolation Violation! "
                    f"Inventory {inventory.id} belongs to farm {inventory.farm_id}, "
                    f"but movement {movement.id} belongs to farm {movement.farm_id}."
                )
            
            new_qty = inventory.qty + qty_delta
            if new_qty < 0:
                # [AGRI-GUARDIAN] STRICT MODE ENFORCEMENT
                raise ValidationError(
                    f"⛔ حظر GRP STRICT: الرصيد غير كافي. "
                    f"المتوفر في {inventory.location.name if inventory.location else 'المخزن'}: {inventory.qty}، "
                    f"المطلوب: {abs(qty_delta)}. لا يُسمح بالمخزون السالب في بيئة الحوكمة الصارمة."
                )
            
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
            
            batch = ItemInventoryBatch.objects.select_for_update().filter(
                inventory=inventory,
                batch_number=batch_num
            ).first()
            
            if batch:
                # [AGRI-GUARDIAN] Strict Expiry Date Processing (GlobalGAP)
                if qty_delta < 0 and batch.expiry_date and batch.expiry_date < timezone.now().date():
                    raise ValidationError(f"⛔ تنبيه GlobalGAP: الصنف '{inventory.item.name}' بالدفعة ({batch_num}) منتهي الصلاحية بتاريخ {batch.expiry_date}. يُحظر استخدامه!")

                old_batch_qty = Decimal(str(batch.qty))
                new_batch_qty = old_batch_qty + qty_delta
                if new_batch_qty < 0:
                     raise ValidationError(f"رصيد التشغيلة {batch_num} غير كافي.")
                
                batch.qty = F('qty') + qty_delta
                batch.save(update_fields=['qty', 'updated_at'])
                batch.refresh_from_db()

                log_sensitive_mutation(
                    actor=actor_user,
                    action="update_sensitive_batch",
                    model_name="ItemInventoryBatch",
                    object_id=batch.pk,
                    reason=movement.note or movement.ref_type or "inventory_batch_update",
                    old_value={"qty": str(old_batch_qty)},
                    new_value={"qty": str(batch.qty)},
                    farm_id=movement.farm_id,
                    context={"batch_number": batch_num, "movement_id": movement.pk},
                )
            else:
                 if qty_delta < 0:
                      raise ValidationError(f"لا يمكن الصرف من تشغيلة غير موجودة: {batch_num}.")
                 
                 new_batch = ItemInventoryBatch.objects.create(
                     inventory=inventory,
                     batch_number=batch_num,
                     expiry_date=movement.expiry_date,
                     qty=qty_delta
                 )
                 
                 log_sensitive_mutation(
                    actor=actor_user,
                    action="create_sensitive_batch",
                    model_name="ItemInventoryBatch",
                    object_id=new_batch.pk,
                    reason=movement.note or movement.ref_type or "inventory_batch_create",
                    old_value=None,
                    new_value={"qty": str(new_batch.qty)},
                    farm_id=movement.farm_id,
                    context={"batch_number": batch_num, "movement_id": movement.pk},
                )
        elif movement.item.requires_batch_tracking:
            raise ValidationError(
                f"الصنف '{inventory.item.name}' خاضع لرقابة الجودة (GlobalGAP) ويجب تحديد رقم التشغيلة (Batch Number) لاستخدامه."
            )
        elif ItemInventoryBatch.objects.filter(inventory=inventory).exists():
            # Legacy fallback: item has batches but requires_batch_tracking is not set.
            # For consumption (negative delta), auto-deduct FIFO across available batches
            # so that DailyLog submissions are not blocked by batch specificity.
            # For receipts (positive delta), skip batch tracking since no batch_number was given.
            if qty_delta < 0:
                remaining = abs(qty_delta)
                fifo_batches = (
                    ItemInventoryBatch.objects
                    .select_for_update()
                    .filter(inventory=inventory, qty__gt=0)
                    .order_by('id')
                )
                for batch in fifo_batches:
                    if remaining <= 0:
                        break
                    deduct = min(Decimal(str(batch.qty)), remaining)
                    # GlobalGAP expiry advisory (non-blocking for non-strict items)
                    if batch.expiry_date and batch.expiry_date < timezone.now().date():
                        logger.warning(
                            "FIFO batch %s for item '%s' is expired (%s). Consuming anyway (non-strict).",
                            batch.batch_number, inventory.item.name, batch.expiry_date,
                        )
                    batch.qty = F('qty') - deduct
                    batch.save(update_fields=['qty', 'updated_at'])
                    batch.refresh_from_db()
                    remaining -= deduct
                if remaining > 0:
                    raise ValidationError(
                        f"رصيد التشغيلات غير كافٍ للصنف '{inventory.item.name}'. "
                        f"الرصيد الكلي للتشغيلات: {abs(qty_delta) - remaining}، المطلوب: {abs(qty_delta)}."
                    )

    @staticmethod
    def _update_moving_average_cost(item: Item, new_qty: Decimal, new_unit_cost: Decimal):
        from decimal import ROUND_HALF_UP # Ensure import
        
        if new_qty <= 0 or new_unit_cost < 0:
            return

        # Lock Item to prevent concurrent cost updates
        item_locked = Item.objects.select_for_update().get(pk=item.pk)
        
        # Calculate Total Value currently in stock
        total_existing_qty = ItemInventory.objects.filter(item=item_locked).aggregate(
            total=Sum('qty')
        )['total'] or Decimal('0')
        
        current_value = total_existing_qty * item_locked.unit_price
        incoming_value = new_qty * new_unit_cost
        
        final_qty = total_existing_qty + new_qty
        
        if final_qty > 0:
            # [Agri-Guardian] Safe Division
            # We use 4 decimal places for internal unit cost to maintain precision for large quantities
            # e.g. Cost = 33.3333, sold 10,000 units -> accurate total.
            COST_PRECISION = Decimal("0.0001")
            
            from decimal import getcontext
            raw_new_map = getcontext().divide(Decimal(str(current_value + incoming_value)), Decimal(str(final_qty)))
            new_map = raw_new_map.quantize(COST_PRECISION, rounding=ROUND_HALF_UP)
            
            item_locked.unit_price = new_map
            item_locked.save(update_fields=['unit_price'])
            
            logger.info(f"Updated MAP for {item.name}: {new_map} (Was: {item.unit_price})")

    @staticmethod
    def get_stock_level(farm: Farm, item: Item, location: Location = None) -> Decimal:
        qs = ItemInventory.objects.filter(farm=farm, item=item)
        if location:
            qs = qs.filter(location=location)
        
        aggregate = qs.aggregate(total_qty=Sum('qty'))
        return aggregate.get('total_qty') or Decimal('0')

    @staticmethod
    def get_batch_stock_level(farm: Farm, item: Item, batch_number: str, location: Location = None) -> Decimal:
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
    def process_consumption(item_id, farm_id, quantity, user, location_id=None):
        """
        [AGRI-GUARDIAN] STRICT STOCK CONTROL
        Prevent negative stock and phantom consumption.
        """
        try:
            qty = quantity if isinstance(quantity, Decimal) else Decimal(str(quantity))
        except (ValueError, TypeError, ArithmeticError):
            raise ValidationError(f"صيغة الكمية غير صالحة: {quantity}")

        if qty <= 0:
            raise ValidationError("الكمية يجب أن تكون أكبر من الصفر.")

        farm = Farm.objects.get(id=farm_id)
        item = Item.objects.get(id=item_id)
        location = Location.objects.get(id=location_id) if location_id else None

        # [Agri-Guardian] Unified transaction routing to ensure:
        # 1. Fiscal Period Compliance (Axis 3)
        # 2. Complete Audit Trace (Axis 7)
        # 3. Batch Level Handling
        return InventoryService.record_movement(
            farm=farm,
            item=item,
            qty_delta=-qty,
            location=location,
            ref_type="CONSUMPTION",
            ref_id=str(getattr(user, "id", "")),
            note="صرف استهلاك عبر ضوابط المخزون الصارمة.",
            actor_user=user
        )

    @staticmethod
    @transaction.atomic
    def process_grn(
        farm: Farm,
        item: Item,
        location: Location,
        qty: Decimal,
        unit_cost: Decimal,
        ref_id: str,
        batch_number: str = None,
        expiry_date = None,
        actor_user=None,
    ):
        # Update cost implies a financial event, should check fiscal period potentially
        # but record_movement will check strict compliance now.
        InventoryService._update_moving_average_cost(item, qty, unit_cost)
        InventoryService.record_movement(
            farm=farm,
            item=item,
            qty_delta=qty,
            location=location,
            ref_type='GRN',
            ref_id=ref_id,
            note=f"استلام مواد: {ref_id} بسعر {unit_cost}",
            batch_number=batch_number,
            expiry_date=expiry_date,
            actor_user=actor_user,
        )

    @staticmethod
    @transaction.atomic
    def transfer_stock(farm: Farm, item: Item, from_loc: Location, to_loc: Location, qty: Decimal, user, batch_number: str = None):
        if qty <= 0:
             raise ValidationError("الكمية يجب أن تكون موجبة.")
        
        # [Agri-Guardian] Farm Isolation Trap
        if from_loc.farm_id != farm.id or to_loc.farm_id != farm.id:
            raise ValidationError("هذه الدالة المخصصة للنقل الداخلي. الموقع لا ينتمي للمزرعة الحالية.")
             
        # [Agri-Guardian] Logic Trap: Prevent Wash Trading (Self-Transfer)
        if from_loc.id == to_loc.id:
            raise ValidationError("لا يمكن نقل المخزون إلى نفس الموقع (حركة صورية).")
             
        # 1. Deduct from Source
        InventoryService.record_movement(
            farm=farm,
            item=item,
            qty_delta=-qty,
            location=from_loc,
            ref_type='TRANSFER_OUT',
            ref_id=f"{from_loc.id}-{to_loc.id}",
            note=f"تحويل إلى {to_loc.name}",
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
            note=f"تحويل من {from_loc.name}",
            batch_number=batch_number,
            actor_user=user,
            
        )

    @staticmethod
    @transaction.atomic
    def record_spoilage(farm: Farm, item: Item, location: Location, qty: Decimal, reason: str, reported_by):
        """
        Records inventory lost due to heat, theft, or damage.
        Separates 'Production Cost' from 'Operational Loss'.
        Protocol XXVI: The Shrinkage Standard.
        """
        if qty <= 0:
             raise ValidationError("كمية الهالك يجب أن تكون موجبة.")

        # 1. Deduct from Physical Stock (Movement Type: ADJUSTMENT or SPOILAGE)
        InventoryService.record_movement(
            farm=farm,
            item=item,
            qty_delta=-qty,
            location=location,
            ref_type='SPOILAGE',
            ref_id=f"LOSS-{timezone.now().strftime('%Y%m%d%H%M')}",
            note=f"تالف/هالك ({reason}) - تم الإبلاغ بواسطة {reported_by}",
            batch_number=None, # Assuming general stock or specific batch passed in future
            actor_user=reported_by
        )
        
        logger.warning(f"تم تسجيل هالك: مزرعة {farm.id}، صنف {item.id}، كمية {qty}، السبب: {reason}")
        
        # 3. Trigger Financial Alert if high value
        financial_loss_value = qty * item.unit_price
        
        # يجب رفع طلب اعتماد إذا تجاوزت القيمة حد الانحراف الحرج
        critical_spoilage_limit = Decimal('50000.0000')
        if financial_loss_value > critical_spoilage_limit:
            raise ValidationError("تتجاوز قيمة الهالك السقف الاستيعابي. الرجاء إنشاء (طلب إتلاف) عبر نظام الاعتمادات.")


class PurchaseOrderService:
    """
    طبقة الخدمة لإدارة أوامر الشراء (Purchase Orders).
    تحقق الامتثال لـ [AGRI-GUARDIAN Law 67]: الكتابة المعاملاتية عبر طبقة الخدمة حصراً.
    """

    @staticmethod
    @transaction.atomic
    def submit_draft(po: PurchaseOrder, user):
        """تحويل مسودة أمر الشراء إلى طلب معلق للمراجعة الفنية."""
        if po.status != PurchaseOrder.Status.DRAFT:
            raise ValidationError("يمكن تقديم المسودات فقط.")
        
        old_status = po.status
        po.status = PurchaseOrder.Status.PENDING_TECHNICAL
        po.save(update_fields=['status', 'updated_at'])

        log_sensitive_mutation(
            actor=user,
            action="update_status",
            model_name="PurchaseOrder",
            object_id=po.pk,
            reason="PO submission for technical review",
            old_value={"status": old_status},
            new_value={"status": po.status},
            farm_id=po.farm_id,
            context={"source": "PurchaseOrderService.submit_draft"}
        )
        return po

    @staticmethod
    @transaction.atomic
    def approve_stage(po: PurchaseOrder, user, role: str):
        """
        اعتماد مرحلة معينة لمسار أمر الشراء.
        يدعم المراجعة الفنية، المالية، واعتماد المدير للمشتريات عالية القيمة.
        """
        if po.status == PurchaseOrder.Status.APPROVED:
            raise ValidationError("أمر الشراء معتمد بالفعل.")

        threshold = po.farm.settings.procurement_committee_threshold
        is_high_value = po.total_amount >= threshold
        old_status = po.status
        update_fields = ['status', 'updated_at']

        if role == 'technical' and po.status == PurchaseOrder.Status.PENDING_TECHNICAL:
            po.technical_signature = user
            update_fields.append('technical_signature')
            if not is_high_value:
                po.status = PurchaseOrder.Status.APPROVED
            else:
                po.status = PurchaseOrder.Status.PENDING_FINANCIAL
        elif role == 'financial' and po.status == PurchaseOrder.Status.PENDING_FINANCIAL:
            po.financial_signature = user
            update_fields.append('financial_signature')
            po.status = PurchaseOrder.Status.PENDING_DIRECTOR
        elif role == 'director' and po.status == PurchaseOrder.Status.PENDING_DIRECTOR:
            po.director_signature = user
            update_fields.append('director_signature')
            po.status = PurchaseOrder.Status.APPROVED
        else:
            raise ValidationError(f"دور غير صالح ({role}) أو حالة طلب ({po.status}) غير متوافقة للاعتماد.")

        po.save(update_fields=update_fields)

        log_sensitive_mutation(
            actor=user,
            action="approve_stage",
            model_name="PurchaseOrder",
            object_id=po.pk,
            reason=f"Approved by {role}",
            old_value={"status": old_status},
            new_value={"status": po.status},
            farm_id=po.farm_id,
            context={"role": role, "is_high_value": is_high_value, "source": "PurchaseOrderService.approve_stage"}
        )
        
        # Forensic Proof
        ForensicService.sign_transaction(
            agent=str(user.username),
            action='PO_APPROVAL',
            payload={
                'po_id': str(po.id),
                'role': role,
                'status': po.status,
                'amount': str(po.total_amount)
            }
        )
        
        return po
