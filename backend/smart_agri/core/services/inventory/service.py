import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from django.db import connection, transaction
from django.core.exceptions import ValidationError

from smart_agri.core.models.activity import Activity
from smart_agri.core.models.crop import CropVariety
from smart_agri.core.models.farm import Location
from smart_agri.core.models.tree import (
    LocationTreeStock,
    TreeStockEvent,
    TreeProductivityStatus,
)
from smart_agri.core.models.log import AuditLog

from smart_agri.core.services.inventory.policy import InventoryPolicy
from smart_agri.core.services.inventory.calculator import TreeEventCalculator, TreeInventoryResult
from smart_agri.core.services.inventory.manager import TreeStockManager

logger = logging.getLogger(__name__)

class TreeInventoryService:
    """
    خدمة مسؤولة عن مزامنة الأنشطة المتعلقة بالأشجار مع سجل الجرد والرصد التاريخي.
    """
    DEFAULT_JUVENILE_YEARS = 3
    DEFAULT_MATURE_YEARS = 7
    DEFAULT_DECLINING_YEARS = 12

    @staticmethod
    def _decimal_or_none(value):
        if value in (None, ""):
            return None
        return Decimal(str(value))

    @staticmethod
    def _harvest_uom_from_activity(activity: Activity) -> str:
        product = getattr(activity, 'product', None)
        if product and getattr(product, 'item', None):
            return product.item.uom or ''
        return ''

    @staticmethod
    def _get_harvest_quantity(activity: Activity):
        ext = getattr(activity, 'harvest_details', None)
        if ext:
            return ext.harvest_quantity
        return TreeInventoryService._decimal_or_none(getattr(activity, 'harvest_quantity', None))

    @staticmethod
    def _get_water_volume(activity: Activity):
        ext = getattr(activity, 'irrigation_details', None)
        if ext:
            return ext.water_volume
        return TreeInventoryService._decimal_or_none(getattr(activity, 'water_volume', None))

    @staticmethod
    def _get_water_uom(activity: Activity) -> str:
        ext = getattr(activity, 'irrigation_details', None)
        if ext:
            return ext.uom or 'm3'
        return getattr(activity, 'water_uom', 'm3')

    @staticmethod
    def _get_fertilizer_quantity(activity: Activity):
        ext = getattr(activity, 'material_details', None)
        if ext:
            return ext.fertilizer_quantity
        return TreeInventoryService._decimal_or_none(getattr(activity, 'fertilizer_quantity', None))
    
    @staticmethod
    def _is_tree_activity(activity: Activity) -> bool:
        # Helper to check if activity relates to tree stock
        return InventoryPolicy.is_tree_tracked(activity)

    def _lock_location_stock(self, activity: Activity):
        """Legacy compatibility wrapper for older tests/services."""
        return TreeStockManager().lock_location_stock(activity)

    @staticmethod
    def _build_event_notes(activity: Activity, user=None) -> str:
        notes = []
        if user:
            notes.append(f"User: {user}")
        if activity.note:
            notes.append(f"Note: {activity.note}")
        material = getattr(activity, "material", "")
        if material:
            notes.append(f"material: {material}")
        log_notes = getattr(activity.log, "notes", "")
        if log_notes:
            notes.append(f"log_notes: {log_notes}")
        return " | ".join(notes)

    def _build_manual_event_notes(self, *, reason: str, additional_notes: Optional[str], user=None) -> str:
        parts = [f"reason: {reason}"]
        if user:
            parts.append(f"user: {getattr(user, 'username', user)}")
        if additional_notes:
            cleaned = str(additional_notes).strip()
            if cleaned:
                parts.append(cleaned)
        return " | ".join(parts)

    @staticmethod
    def _append_manual_adjustment_audit(
        *,
        actor,
        stock: LocationTreeStock,
        previous_count: int,
        resulting_count: int,
        delta_value: int,
        reason: str,
        source: Optional[str],
        notes: Optional[str],
        event: TreeStockEvent,
    ) -> None:
        AuditLog.objects.create(
            actor=actor,
            farm=getattr(getattr(stock, "location", None), "farm", None),
            action="TREE_STOCK_MANUAL_ADJUSTMENT",
            model="LocationTreeStock",
            object_id=str(stock.pk),
            old_payload={
                "current_tree_count": int(previous_count or 0),
                "location_id": stock.location_id,
                "crop_variety_id": stock.crop_variety_id,
            },
            new_payload={
                "current_tree_count": int(resulting_count or 0),
                "delta": int(delta_value or 0),
                "location_id": stock.location_id,
                "crop_variety_id": stock.crop_variety_id,
                "event_id": event.pk,
                "source": source or "",
                "notes": notes or "",
            },
            reason=(reason or "").strip(),
        )

    @classmethod
    def determine_event_type(
        cls,
        activity: Activity,
        *,
        delta: Optional[int] = None,
        stock_changed: bool = False,
        previous_event: TreeStockEvent | None = None,
    ) -> Optional[str]:
        """Return the most suitable tree stock event type for ``activity``."""
        if activity is None:
            return None

        resolved_delta = int(delta if delta is not None else (activity.tree_count_delta or 0))

        if not stock_changed and not InventoryPolicy.is_tree_tracked(activity):
            return None

        # Pre-check harvest without quantity (Business Rule)
        if (
            activity.task
            and getattr(activity.task, "is_harvest_task", False)
            and getattr(activity, "harvest_quantity", None) is None
            and getattr(getattr(activity, "harvest_details", None), "harvest_quantity", None) is None
        ):
            return None

        calculator = TreeEventCalculator()
        return calculator.compute_event_type(
            activity,
            resolved_delta,
            stock_changed=stock_changed,
            existing_event=previous_event,
        )

    @classmethod
    def record_event_from_activity(
        cls,
        activity: Activity,
        *,
        user=None,
        delta_change: Optional[int] = None,
        previous_delta: Optional[int] = None,
        activity_tree_count_change: Optional[int] = None,
        previous_activity_tree_count: Optional[int] = None,
        previous_location: Location | None = None,
        previous_variety: CropVariety | None = None,
    ) -> Optional[TreeStockEvent]:
        """Create or update a :class:`TreeStockEvent` based on the supplied activity."""
        if activity is None:
            return None

        service = cls()
        result = service.reconcile_activity(
            activity=activity,
            user=user,
            delta_change=delta_change,
            previous_delta=previous_delta,
            activity_tree_count_change=activity_tree_count_change,
            previous_activity_tree_count=previous_activity_tree_count,
            previous_location=previous_location,
            previous_variety=previous_variety,
        )

        return result.event if result else None

    def reconcile_activity(
        self,
        *,
        activity: Activity,
        user=None,
        previous_delta: Optional[int] = None,
        delta_change: Optional[int] = None,
        activity_tree_count_change: Optional[int] = None,
        previous_activity_tree_count: Optional[int] = None,
        previous_location: Location | None = None,
        previous_variety: CropVariety | None = None,
        stock: Optional[LocationTreeStock] = None,
    ) -> Optional[TreeInventoryResult]:
        
        if not self._is_tree_activity(activity):
            logger.debug("النشاط %s لا يعتبر نشاطاً لتتبع الأشجار", activity.pk)
            return None

        InventoryPolicy.validate_activity_for_stock(activity)

        stock_manager = TreeStockManager()
        calculator = TreeEventCalculator()
        
        new_delta = activity.tree_count_delta or 0

        with transaction.atomic():
            pre_locked_map = {}
            if stock is None:
                 loc = activity.activity_locations.first()
                 location_id = loc.location_id if loc else None
                 target_key = (location_id, activity.variety_id)
                 stock_keys = {target_key}
                 
                 existing_event = TreeStockEvent.objects.filter(activity=activity).select_related('location_tree_stock').first()
                 if existing_event and existing_event.location_tree_stock:
                     s = existing_event.location_tree_stock
                     stock_keys.add((s.location_id, s.crop_variety_id))
                 
                 sorted_keys = sorted(list(stock_keys)) 
                 if sorted_keys:
                    from django.db.models import Q
                    q_filter = Q()
                    for l, v in sorted_keys:
                        q_filter |= Q(location_id=l, crop_variety_id=v)
                    
                    qs = LocationTreeStock.objects.filter(q_filter).order_by('location_id', 'crop_variety_id')
                    if connection.vendor == "postgresql":
                        qs = qs.select_for_update()
                    
                    for s in qs:
                        pre_locked_map[(s.location_id, s.crop_variety_id)] = s

                 stock = pre_locked_map.get(target_key)
                 if not stock:
                     stock = stock_manager.lock_location_stock(activity)
            else:
                 existing_event = TreeStockEvent.objects.filter(activity=activity).select_related('location_tree_stock').first()

            if existing_event:
                 old_stock_id = existing_event.location_tree_stock_id
                 if old_stock_id != stock.pk:
                       # Context change logic handled by locking/manager
                       pass
            
            effective_previous_delta = previous_delta
            if existing_event and effective_previous_delta is None:
                    effective_previous_delta = existing_event.tree_count_delta or 0
            elif effective_previous_delta is None:
                effective_previous_delta = 0

            effective_delta_change = delta_change
            if effective_delta_change is None:
                effective_delta_change = new_delta - (effective_previous_delta or 0)

            if existing_event:
                old_stock_id_val = existing_event.location_tree_stock_id
                stock_changed = (old_stock_id_val != stock.pk)

                if stock_changed:
                    old_stock_ref = LocationTreeStock.objects.get(pk=old_stock_id_val)
                    old_stock_ref = stock_manager.lock_existing_stock(old_stock_ref)
                    
                    if effective_previous_delta:
                         stock_manager.apply_stock_delta(old_stock_ref, -effective_previous_delta)
                    
                    stock = stock_manager.apply_stock_delta(stock, new_delta)
                    
                else:
                    stock = stock_manager.apply_stock_delta(stock, effective_delta_change)

            else:
                 stock = stock_manager.apply_stock_delta(stock, effective_delta_change)

            resulting_count = calculator.resolve_resulting_count(
                activity=activity,
                stock=stock,
                existing_event=existing_event,
                activity_tree_count_change=activity_tree_count_change,
                previous_activity_tree_count=previous_activity_tree_count,
            )

            event_type = calculator.compute_event_type(
                activity,
                new_delta,
                stock_changed=(existing_event and existing_event.location_tree_stock_id != stock.pk),
                existing_event=existing_event,
            )
            
            if existing_event:
                existing_event.location_tree_stock = stock
                existing_event.event_type = event_type
                existing_event.tree_count_delta = new_delta
                existing_event.resulting_tree_count = resulting_count
                existing_event.loss_reason = activity.tree_loss_reason if new_delta < 0 else None
                existing_event.planting_date = stock.planting_date
                existing_event.source = stock.source
                existing_event.harvest_quantity = self._get_harvest_quantity(activity)
                existing_event.harvest_uom = self._harvest_uom_from_activity(activity)
                existing_event.water_volume = self._get_water_volume(activity)
                existing_event.water_uom = self._get_water_uom(activity)
                existing_event.fertilizer_quantity = self._get_fertilizer_quantity(activity)
                existing_event.fertilizer_uom = getattr(activity, "fertilizer_uom", None)
                existing_event.notes = self._build_event_notes(activity, user=user)
                existing_event.save()
                return TreeInventoryResult(stock=stock, event=existing_event)
            else:
                event = TreeStockEvent.objects.create(
                    location_tree_stock=stock,
                    activity=activity,
                    event_type=event_type,
                    tree_count_delta=new_delta,
                    resulting_tree_count=resulting_count,
                    loss_reason=activity.tree_loss_reason if new_delta < 0 else None,
                    planting_date=stock.planting_date,
                    source=stock.source,
                    harvest_quantity=self._get_harvest_quantity(activity),
                    harvest_uom=self._harvest_uom_from_activity(activity),
                    water_volume=self._get_water_volume(activity),
                    water_uom=self._get_water_uom(activity),
                    fertilizer_quantity=self._get_fertilizer_quantity(activity),
                    fertilizer_uom=getattr(activity, "fertilizer_uom", None),
                    notes=self._build_event_notes(activity, user=user),
                )
                return TreeInventoryResult(stock=stock, event=event)

    @classmethod
    def bulk_process_activities(cls, activities: Iterable[Activity], *, user=None) -> Tuple[int, list[int]]:
        processed = 0
        failed = []

        if not activities:
            return 0, []

        raw_list = list(activities)
        if not raw_list:
             return 0, []
        
        pks = [a.pk for a in raw_list if getattr(a, 'pk', None)]
        
        activities_list = list(
            Activity.objects.filter(pk__in=pks)
            .select_related('variety', 'task', 'log', 'product__item', 'tree_loss_reason')
            .prefetch_related('activity_locations')
            .order_by('pk') 
        )

        stock_keys = set()
        for act in activities_list:
            loc = act.activity_locations.first()
            if loc and loc.location_id and act.variety_id:
                stock_keys.add((loc.location_id, act.variety_id))
        
        existing_events = TreeStockEvent.objects.filter(
            activity__in=activities_list
        ).select_related('location_tree_stock')
        
        for event in existing_events:
            s = event.location_tree_stock
            if s:
                stock_keys.add((s.location_id, s.crop_variety_id))

        sorted_keys = sorted(list(stock_keys)) 
        service = cls()

        try:
            with transaction.atomic():
                from django.db.models import Q
                stock_filter = Q()
                for loc_id, var_id in sorted_keys:
                    stock_filter |= Q(location_id=loc_id, crop_variety_id=var_id)
                
                stock_map: Dict[Tuple[int, int], LocationTreeStock] = {}
                
                if stock_filter:
                    stocks_qs = LocationTreeStock.objects.filter(stock_filter).order_by('location_id', 'crop_variety_id')
                    if connection.vendor == "postgresql":
                        stocks_qs = stocks_qs.select_for_update()
                    
                    for s in stocks_qs:
                        stock_map[(s.location_id, s.crop_variety_id)] = s

                for activity in activities_list:
                    # Target Stock
                    loc = activity.activity_locations.first()
                    location_id = loc.location_id if loc else None
                    target_stock = stock_map.get((location_id, activity.variety_id))
                    try:
                        result = service.reconcile_activity(activity=activity, user=user, stock=target_stock)
                        if result and result.event:
                            processed += 1
                    except ValidationError as e:
                        logger.error(f"Validation error: {e}")
                        raise
                    except (ValidationError, OperationalError, ValueError) as e:
                        logger.exception("Bulk process error")
                        raise

        except (ValidationError, OperationalError, ValueError) as e:
            logger.error(f"Bulk process aborted: {e}")
            failed = [getattr(a, "pk", None) for a in activities_list]
            processed = 0
            
        return processed, failed

    def reverse_activity(self, *, activity: Activity, user=None) -> Optional[TreeInventoryResult]:
        with transaction.atomic():
            event_qs = TreeStockEvent.objects.filter(activity=activity)
            if connection.vendor == "postgresql":
                event_qs = event_qs.select_for_update()
            event = event_qs.first()
            if not event:
                if not self._is_tree_activity(activity):
                    logger.debug(" %s     ", activity.pk)
                    return None
                logger.debug("         %s", activity.pk)
                return None

            stock_manager = TreeStockManager()
            stock = stock_manager.lock_existing_stock(event.location_tree_stock)
            delta = event.tree_count_delta or 0
            if delta:
                stock = stock_manager.apply_stock_delta(stock, -delta)

            event.delete()

        logger.info(
            "    ", extra={"activity_id": activity.pk, "delta": delta}
        )
        return TreeInventoryResult(stock=stock, event=event)

    def manual_adjustment(
        self,
        *,
        stock: LocationTreeStock | None = None,
        location: Location | None = None,
        variety: CropVariety | None = None,
        resulting_tree_count: Optional[int] = None,
        delta: Optional[int] = None,
        planting_date: Optional[date] = None,
        source: Optional[str] = None,
        reason: str,
        notes: Optional[str] = None,
        user=None,
    ) -> TreeInventoryResult:
        """تنفيذ تعديل يدوي على جرد الأشجار مع إنشاء حدث مرتبط."""
        stock_manager = TreeStockManager()

        # Validation from Policy
        InventoryPolicy.validate_manual_adjustment(resulting_tree_count, delta, reason)

        with transaction.atomic():
            if stock:
                locked_stock = stock_manager.lock_existing_stock(stock)
            elif location and variety:
                # Manual usage of select_for_update to match Manager pattern
                locked_stock = LocationTreeStock.objects.select_for_update().filter(location=location, crop_variety=variety).first()
                if not locked_stock:
                     # Create new (Safe Create via Manager logic if exposed, or manual here)
                     # Manager doesn't expose safe_create publically in the snippet, doing it manually here roughly strictly.
                     # But manager.lock_location_stock(activity) does it. Here we don't have activity.
                     # We replicate creation logic.
                     status = stock_manager._default_productivity_status()
                     locked_stock = LocationTreeStock.objects.create(
                        location=location,
                        crop_variety=variety,
                        current_tree_count=0,
                        productivity_status=status,
                        planting_date=planting_date,
                        source=source or "",
                    )
            else:
                 raise ValidationError("يجب تحديد المخزون أو (الموقع + الصنف)")

            original_count = locked_stock.current_tree_count or 0
            if resulting_tree_count is not None:
                delta_value = resulting_tree_count - original_count
            else:
                delta_value = delta or 0

            locked_stock = stock_manager.apply_stock_delta(locked_stock, delta_value)
            
            updates = []
            if planting_date is not None:
                locked_stock.planting_date = planting_date
                updates.append("planting_date")
            if source is not None:
                locked_stock.source = source
                updates.append("source")
            
            if updates:
                locked_stock.save(update_fields=updates)
                stock_manager._update_productivity_status(locked_stock)

            event_type = (
                TreeStockEvent.ADJUSTMENT if delta_value != 0 else TreeStockEvent.INSPECTION
            )
            event = TreeStockEvent.objects.create(
                location_tree_stock=locked_stock,
                event_type=event_type,
                tree_count_delta=delta_value,
                resulting_tree_count=locked_stock.current_tree_count,
                planting_date=locked_stock.planting_date,
                source=locked_stock.source,
                notes=self._build_manual_event_notes(
                    reason=reason, additional_notes=notes, user=user
                ),
            )
            self._append_manual_adjustment_audit(
                actor=user,
                stock=locked_stock,
                previous_count=original_count,
                resulting_count=locked_stock.current_tree_count,
                delta_value=delta_value,
                reason=reason,
                source=locked_stock.source,
                notes=notes,
                event=event,
            )

        logger.info(
            "تم تنفيذ تعديل يدوي لمخزون الأشجار", extra={
                "stock_id": locked_stock.pk,
                "delta": delta_value,
                "resulting_count": locked_stock.current_tree_count,
            }
        )
        return TreeInventoryResult(stock=locked_stock, event=event)

    def refresh_productivity_status(
        self,
        *,
        queryset=None,
        batch_size: int = 200,
        as_of: Optional[date] = None,
    ) -> dict[str, float | int]:
        from smart_agri.core.services.tree_productivity import TreeProductivityService
        service = TreeProductivityService()
        return service.refresh_productivity_status(
            queryset=queryset,
            batch_size=batch_size,
            as_of=as_of
        )

    def sync_service_coverages(
        self,
        *,
        activity: Activity,
        entries: Sequence[Dict[str, Any]],
        recorded_by=None,
    ) -> None:
        from smart_agri.core.services.tree_coverage import TreeCoverageService
        service = TreeCoverageService()
        return service.sync_service_coverages(
            activity=activity,
            entries=entries,
            recorded_by=recorded_by
        )
