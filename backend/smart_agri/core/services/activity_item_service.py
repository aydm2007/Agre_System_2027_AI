from decimal import Decimal, InvalidOperation
from django.db import transaction, models, OperationalError
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Sum
from smart_agri.core.models import Activity, ActivityItem, Item
from smart_agri.core.services.costing import calculate_activity_cost
from smart_agri.core.services.custody_transfer_service import CustodyTransferService
import logging

_logger = logging.getLogger(__name__)

# [AGRI-GUARDIAN §8.III] BOM Deviation Threshold
BOM_DEVIATION_THRESHOLD = Decimal("0.20")  # 20% max deviation

class ActivityItemService:
    """
    Service for managing Activity Items.
    Ensures that every change to an item triggers a cost recalculation for the parent activity.
    """

    @staticmethod
    def _recalculate_cost_non_blocking(activity: Activity):
        materials_total = (
            ActivityItem.objects.filter(activity=activity, deleted_at__isnull=True)
            .select_related('item')
            .aggregate(
                total=Sum(
                    models.F('applied_qty') * models.F('item__unit_price'),
                    output_field=models.DecimalField(max_digits=19, decimal_places=4),
                )
            )
            .get('total')
            or Decimal("0.00")
        )
        materials_total = materials_total.quantize(Decimal("0.0001"))
        wastage_total = (
            ActivityItem.objects.filter(activity=activity, deleted_at__isnull=True)
            .select_related('item')
            .aggregate(
                total=Sum(
                    models.F('waste_qty') * models.F('item__unit_price'),
                    output_field=models.DecimalField(max_digits=19, decimal_places=4),
                )
            )
            .get('total')
            or Decimal("0.00")
        ).quantize(Decimal("0.0001"))

        try:
            calculate_activity_cost(activity)
            activity.refresh_from_db(fields=['cost_total', 'cost_materials', 'cost_wastage'])
        except (ValueError, ValidationError) as exc:
            _logger.warning("Cost recalculation skipped for activity %s: %s", activity.pk, exc)

        # Legacy fallback alignment: always keep material rollup deterministic
        # even when strict costing dependencies are absent.
        other_costs = (
            Decimal(str(getattr(activity, "cost_labor", 0) or 0))
            + Decimal(str(getattr(activity, "cost_machinery", 0) or 0))
            + Decimal(str(getattr(activity, "cost_overhead", 0) or 0))
            + Decimal(str(getattr(activity, "cost_wastage", 0) or 0))
        ).quantize(Decimal("0.0001"))
        activity.cost_materials = materials_total
        activity.cost_wastage = wastage_total
        activity.cost_total = (materials_total + wastage_total + other_costs).quantize(Decimal("0.0001"))
        activity.save(update_fields=['cost_materials', 'cost_wastage', 'cost_total'])

    @staticmethod
    @transaction.atomic
    def create_item(
        activity: Activity,
        item: Item,
        qty: Decimal,
        user=None,
        uom: str = None,
        batch_number: str = None,
        applied_qty: Decimal = None,
        waste_qty: Decimal = None,
        waste_reason: str = "",
    ) -> ActivityItem:
        """
        Creates an ActivityItem and recalculates activity costs.
        """
        if any(isinstance(val, float) for val in [qty, applied_qty, waste_qty]):
            raise ValidationError("SECURITY [Axis-5]: Floating point values are strictly banned in financial services. Use Decimal.")

        if not isinstance(qty, Decimal):
             qty = Decimal(str(qty or "0"))
        applied_qty = Decimal(str(applied_qty if applied_qty is not None else qty))
        waste_qty = Decimal(str(waste_qty if waste_qty is not None else Decimal("0")))
             
        if qty < 0:
            raise ValidationError("لا يمكن أن تكون الكمية سالبة.")
        if applied_qty < 0 or waste_qty < 0:
            raise ValidationError("كميات التطبيق والهدر لا يمكن أن تكون سالبة.")
        if (applied_qty + waste_qty).quantize(Decimal("0.001")) != qty.quantize(Decimal("0.001")):
            raise ValidationError("يجب أن يساوي applied_qty + waste_qty إجمالي الكمية.")

        # [AGRI-GUARDIAN §17] Forensic Cost Snapshot
        # Freeze the unit price at create-time to prevent historical cost leakage.
        snapshot_cost = Decimal(str(item.unit_price or "0"))

        activity_item = ActivityItem.objects.create(
            activity=activity,
            item=item,
            qty=qty,
            applied_qty=applied_qty,
            waste_qty=waste_qty,
            waste_reason=waste_reason or "",
            uom=uom or item.uom,
            batch_number=batch_number,
            cost_per_unit=snapshot_cost
        )

        # Trigger cost recalculation (non-blocking for legacy flows lacking rate setup)
        ActivityItemService._recalculate_cost_non_blocking(activity)
        
        # Sync Financial Ledger
        from smart_agri.core.services.activity_service import ActivityService
        if hasattr(ActivityService, "_sync_ledger"):
            ActivityService._sync_ledger(activity, user)

        # Inventory is handled by ActivityItem signals to avoid double-deduction.
        if getattr(activity.log, "supervisor_id", None):
            CustodyTransferService.refresh_status_for_item(
                farm=activity.log.farm,
                supervisor=activity.log.supervisor,
                item=item,
            )

        # [AGRI-GUARDIAN §8.III] BOM Deviation Advisory Check (Real-time).
        # After consuming material, check cumulative usage vs CropMaterial BOM.
        # Advisory only — does NOT block. Formal reports via `check_bom_deviation` command.
        try:
            ActivityItemService._check_bom_deviation(activity, item, user)
        except (ValidationError, ObjectDoesNotExist, OperationalError) as e:
            _logger.warning("BOM deviation check failed: %s", e)

        return activity_item

    @staticmethod
    def _check_bom_deviation(activity: Activity, item: Item, user):
        """
        [AGRI-GUARDIAN §8.III] Real-time BOM deviation advisory (Ultimate Edition).
        Checks if cumulative material usage for this crop plan exceeds the strict CropRecipe BOM.
        """
        crop_plan = getattr(activity, 'crop_plan', None)
        if not crop_plan:
            return

        # 1. Ultimate Edition Agronomic BOM Resolution
        recipe = getattr(crop_plan, 'recipe', None)
        per_ha_qty = Decimal("0")

        if not recipe:
            # Fallback to legacy CropMaterial if no rigorous recipe is assigned
            from smart_agri.core.models.crop import CropMaterial
            bom = CropMaterial.objects.filter(
                crop=crop_plan.crop,
                item=item,
                deleted_at__isnull=True,
                recommended_qty__isnull=False,
            ).first()
            if not bom or not bom.recommended_qty or bom.recommended_qty <= 0:
                return
            per_ha_qty = bom.recommended_qty
        else:
            # Strict Agronomic Intelligence BOM (Phase 3)
            from smart_agri.core.models.crop import CropRecipeMaterial
            recipe_mat = CropRecipeMaterial.objects.filter(
                recipe=recipe,
                material__item=item,
            ).first()
            
            if recipe_mat and recipe_mat.standard_qty_per_ha and recipe_mat.standard_qty_per_ha > 0:
                per_ha_qty = recipe_mat.standard_qty_per_ha

        # Calculate recommended total based on plan area
        plan_area = getattr(crop_plan, 'area', None) or Decimal("1")
        expected_total = per_ha_qty * plan_area

        # Sum all actual usage of this item across all activities in this crop plan
        actual_usage = ActivityItem.objects.filter(
            activity__crop_plan=crop_plan,
            item=item,
            deleted_at__isnull=True,
        ).aggregate(total=Sum('qty'))['total'] or Decimal("0")

        # Deviation Mathematics
        deviation = Decimal("0")
        deviation_pct = Decimal("0")
        is_breach = False

        if expected_total == 0 and actual_usage > 0:
            deviation_pct = Decimal("100.00") # Infinite variance 
            is_breach = True
        elif expected_total > 0:
            from decimal import getcontext
            deviation = getcontext().divide(actual_usage - expected_total, expected_total)
            deviation_pct = (deviation * Decimal("100")).quantize(Decimal("0.1"))
            if deviation > BOM_DEVIATION_THRESHOLD:
                is_breach = True
        else:
            return # 0 expected, 0 actual

        if is_breach:
            from smart_agri.core.models.log import MaterialVarianceAlert
            status = MaterialVarianceAlert.STATUS_CRITICAL if expected_total == 0 else MaterialVarianceAlert.STATUS_WARNING

            alert_msg = (
                f"تنبيه [AGRI-GUARDIAN]: كمية المادة {item.name} المستهلكة "
                f"({actual_usage}) تتجاوز الوصفة المعيارية المعتمدة ({expected_total}) بـ {deviation_pct}%."
            )
            _logger.warning(alert_msg)

            from smart_agri.core.services.sensitive_audit import log_sensitive_mutation
            log_sensitive_mutation(
                actor=user,
                action="bom_deviation_alert",
                model_name="ActivityItem",
                object_id=activity.pk,
                reason=alert_msg,
                old_value={"expected_total": str(expected_total)},
                new_value={"actual_usage": str(actual_usage), "deviation_pct": str(deviation_pct)},
                farm_id=getattr(activity.log, 'farm_id', None),
                context={"source": "variance_engine_v3"},
            )
            
            # Fire the persistent database Alert!
            MaterialVarianceAlert.objects.create(
                log=activity.log,
                crop_plan=crop_plan,
                item=item,
                actual_qty=actual_usage,
                expected_qty=expected_total,
                deviation_pct=deviation_pct,
                status=status,
                note=alert_msg
            )

    @staticmethod
    @transaction.atomic
    def update_item(
        activity_item: ActivityItem,
        user=None,
        qty: Decimal = None,
        uom: str = None,
        batch_number: str = None,
        applied_qty: Decimal = None,
        waste_qty: Decimal = None,
        waste_reason: str = None,
    ) -> ActivityItem:
        """
        Updates an ActivityItem and recalculates activity costs.
        Syncs Inventory differences (Consume more or Restock).
        """
        old_qty = activity_item.qty
        
        if batch_number is not None:
            activity_item.batch_number = batch_number
        
        item_attr = {}
        
        if any(isinstance(val, float) for val in [qty, applied_qty, waste_qty] if val is not None):
             raise ValidationError("SECURITY [Axis-5]: Floating point values are strictly banned in financial services. Use Decimal.")

        if qty is not None:
             item_attr['qty'] = Decimal(str(qty))
        if applied_qty is not None:
             item_attr['applied_qty'] = Decimal(str(applied_qty))
        if waste_qty is not None:
             item_attr['waste_qty'] = Decimal(str(waste_qty))
        if waste_reason is not None:
             item_attr['waste_reason'] = waste_reason
        if uom is not None:
             item_attr['uom'] = uom
        if batch_number is not None:
             item_attr['batch_number'] = batch_number

        # Update snapshot if item changed? Or if we want to refresh snapshot.
        # Usually, once snapshotted, it stays unless intentionally updated.
        # But if the item changes, we MUST update the snapshot.
        current_item = item_attr.get('item', activity_item.item)
        item_attr['cost_per_unit'] = Decimal(str(current_item.unit_price or "0"))

        for attr, value in item_attr.items():
            setattr(activity_item, attr, value)
        
        if activity_item.qty < 0:
            raise ValidationError("لا يمكن أن تكون الكمية سالبة.")
        if activity_item.applied_qty < 0 or activity_item.waste_qty < 0:
            raise ValidationError("كميات التطبيق والهدر لا يمكن أن تكون سالبة.")
        if (
            Decimal(str(activity_item.applied_qty or 0)) + Decimal(str(activity_item.waste_qty or 0))
        ).quantize(Decimal("0.001")) != Decimal(str(activity_item.qty or 0)).quantize(Decimal("0.001")):
            raise ValidationError("يجب أن يساوي applied_qty + waste_qty إجمالي الكمية.")
        

        activity_item.save()

        # Handle Inventory Delta
        if qty is not None and qty != old_qty:
            diff = qty - old_qty
            # If diff > 0: We need MORE (consume, so negative delta) -> -diff
            # If diff < 0: We return STOCK (restock, so positive delta) -> -diff (diff is neg, so -(-x) = +x)
            # Logic: We consumed 'old_qty' (Movement = -old_qty).
            # We want total consumption to be 'qty' (Movement = -qty).
            # Adjustment = (-qty) - (-old_qty) = old_qty - qty = -(qty - old_qty) = -diff.
            
            from smart_agri.core.services.inventory_service import InventoryService
            try:
                InventoryService.record_movement(
                    farm=activity_item.activity.log.farm,
                    item=activity_item.item,
                    qty_delta=-diff,
                    location=CustodyTransferService.get_consumption_location_for_activity(
                        activity=activity_item.activity,
                        item=activity_item.item,
                        required_qty=abs(diff) if diff > 0 else Decimal("0.000"),
                    ),
                    ref_type='activity',
                    ref_id=str(activity_item.activity.id),
                    note=f"Activity Item Update: {activity_item.activity.pk} (Diff: {-diff})"
                )
            except ValueError as e:
                _logger.warning("Inventory missing for update delta: %s", e)

        # Trigger cost recalculation (non-blocking for legacy flows lacking rate setup)
        ActivityItemService._recalculate_cost_non_blocking(activity_item.activity)

        # Sync Financial Ledger
        from smart_agri.core.services.activity_service import ActivityService
        if hasattr(ActivityService, "_sync_ledger"):
            ActivityService._sync_ledger(activity_item.activity, user)
        if getattr(activity_item.activity.log, "supervisor_id", None):
            CustodyTransferService.refresh_status_for_item(
                farm=activity_item.activity.log.farm,
                supervisor=activity_item.activity.log.supervisor,
                item=activity_item.item,
            )

        return activity_item

    @staticmethod
    @transaction.atomic
    def delete_item(activity_item: ActivityItem, user=None) -> None:
        """
        Soft deletes an ActivityItem and recalculates activity costs.
        """
        activity = activity_item.activity
        # Capture state for reversal
        item_to_restore = activity_item.item
        qty_to_restore = activity_item.qty
        
        activity_item.delete()

        # Trigger cost recalculation (non-blocking for legacy flows lacking rate setup)
        ActivityItemService._recalculate_cost_non_blocking(activity)

        # Sync Financial Ledger
        from smart_agri.core.services.activity_service import ActivityService
        if hasattr(ActivityService, "_sync_ledger"):
            ActivityService._sync_ledger(activity, user)

        # Soft-delete does not trigger post_delete in this model, so we reverse inventory explicitly.
        from smart_agri.core.services.inventory_service import InventoryService
        try:
            InventoryService.record_movement(
                farm=activity.log.farm,
                item=item_to_restore,
                qty_delta=qty_to_restore,
                location=CustodyTransferService.get_consumption_location_for_activity(
                    activity=activity,
                    item=item_to_restore,
                    required_qty=Decimal("0.000"),
                ),
                ref_type='activity',
                ref_id=str(activity.id),
                note=f"Activity Item Removal: {activity.pk}"
            )
        except ValueError as e:
            _logger.warning("Inventory missing for removal delta: %s", e)
        if getattr(activity.log, "supervisor_id", None):
            CustodyTransferService.refresh_status_for_item(
                farm=activity.log.farm,
                supervisor=activity.log.supervisor,
                item=item_to_restore,
            )

    @staticmethod
    @transaction.atomic
    def batch_process_items(activity: Activity, items_payload: list, user=None, replace_existing: bool = False):
        """
        Handles batch creation or replacement of activity items.
        Centralizes logic for 'The Trinity' (Inventory + Ledger + Costing) for bulk operations.
        """
        first_loc = activity.activity_locations.first()
        location_id = first_loc.location_id if first_loc else None

        if not items_payload and replace_existing:
             # Just clear existing items
             existing_items = list(ActivityItem.objects.filter(activity=activity))
             for item in existing_items:
                 ActivityItemService.delete_item(item, user)
             return

        if not items_payload:
            return

        # 0. Context Validation
        # Only require location/log if we are actually about to process materials
        if activity.log_id is None or location_id is None:
            raise ValidationError({'items': 'يجب تحديد السجل والموقع قبل إضافة المواد.'})

        farm_id = activity.log.farm_id

        # 1. Validation (Shortages)
        from smart_agri.core.models import ItemInventory, Item
        shortages = []
        
        # We need to consider current stock vs requested. 
        # If replacing, we should theoretically key "reserved stock" from current items back to pool?
        # Actually, if we use 'select_for_update', we can simulate the "Return" then "Check".
        
        # However, to avoid complexity, we can do a naive check first.
        # But for 'replace_existing', we SHOULD return stock first to allow re-consumption of same items.
        
        if replace_existing:
             existing_items = list(ActivityItem.objects.filter(activity=activity))
             for item in existing_items:
                 ActivityItemService.delete_item(item, user)
        
        # [AGRI-GUARDIAN FIX] Pre-aggregate quantities to prevent over-consumption via duplicates
        required_qty_map = {}
        for entry in items_payload:
            item_ref = entry.get('item') or entry.get('item_id')
            item_id_str = str(item_ref.pk) if isinstance(item_ref, Item) else str(item_ref.get("id")) if isinstance(item_ref, dict) else str(item_ref)
            qty_token = entry.get('qty') or entry.get('quantity')
            if not item_id_str or item_id_str == 'None':
                continue
            try:
                qty = Decimal(str(qty_token))
            except (ValueError, TypeError, InvalidOperation):
                continue
            if qty > 0:
                required_qty_map[item_id_str] = required_qty_map.get(item_id_str, Decimal('0')) + qty
                
        # We also need a set to track if we already alerted about a shortage for an item, to avoid dup messages
        shortage_alerted_items = set()

        # Now process new items
        for entry in items_payload:
            item_ref = entry.get('item') or entry.get('item_id')
            if isinstance(item_ref, Item):
                item_id = item_ref.pk
            elif isinstance(item_ref, dict):
                item_id = item_ref.get("id")
            else:
                item_id = item_ref
            
            item_id_str = str(item_id)
            qty_token = entry.get('qty') or entry.get('quantity')
            uom = entry.get('uom') or ''
            batch_number = entry.get('batch_number')
            
            if not item_id:
                continue
            try:
                qty = Decimal(str(qty_token))
            except (ValueError, TypeError, InvalidOperation) as e:
                import logging
                logging.getLogger(__name__).warning(f"Invalid qty '{qty_token}' for item {item_id}: {e}")
                continue  # Skip invalid entries instead of defaulting to 0
            if qty <= 0:
                continue
            
            if item_id_str in shortage_alerted_items:
                continue

            item_obj = Item.objects.get(pk=item_id)
            try:
                source_location = CustodyTransferService.get_consumption_location_for_activity(
                    activity=activity,
                    item=item_obj,
                    required_qty=required_qty_map.get(item_id_str, qty),
                )
            except ValidationError as exc:
                raise

            inv_filters = {'farm_id': farm_id, 'item_id': item_id}
            if source_location:
                inv_filters['location_id'] = source_location.id
            else:
                inv_filters['location_id__isnull'] = True

            inventory_at_location = (
                ItemInventory.objects.select_for_update()
                .filter(**inv_filters)
                .first()
            )
            on_hand = inventory_at_location.qty if inventory_at_location else Decimal('0')
            
            total_requested = required_qty_map.get(item_id_str, qty)

            if total_requested > on_hand:
                _logger.error(
                    "ITEM SHORTAGE: Item %s, Farm %s, Location %s, Req %s, OnHand %s",
                    item_id, farm_id, source_location, total_requested, on_hand
                )
                shortages.append(
                    f"الصنف رقم ({item_id}) لا يتوفر بكمية كافية. "
                    f"الكمية المتاحة: {on_hand}، إجمالي المطلوب (لجميع السطور المطلوبة): {total_requested}."
                )
                shortage_alerted_items.add(item_id_str)
                continue
            
            # Create (Safe)
            ActivityItemService.create_item(
                activity=activity,
                item=item_obj,
                qty=qty,
                user=user,
                uom=uom,
                batch_number=batch_number,
                applied_qty=entry.get('applied_qty') or qty,
                waste_qty=entry.get('waste_qty') or Decimal('0'),
                waste_reason=entry.get('waste_reason') or '',
            )

        if shortages:
             # If we already deleted items (replace=True) and now hit shortage, we have a partial state?
             # transaction.atomic will rollback EVERYTHING including the deletes. Safe.
             raise ValidationError({'items': shortages})
