import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
from django.db import transaction, OperationalError, IntegrityError
from django.core.exceptions import ValidationError, PermissionDenied
from django.conf import settings
from smart_agri.core.models.activity import (
    Activity, ActivityHarvest, ActivityIrrigation, 
    ActivityMaterialApplication, ActivityMachineUsage
)
from smart_agri.core.models.tree import TreeLossReason
from smart_agri.core.models import StockMovement
from smart_agri.core.models.task import Task
from smart_agri.finance.models import FinancialLedger
from smart_agri.core.models.log import DailyLog
from smart_agri.core.services.costing.policy import CostPolicy
from smart_agri.core.services.activity_labor import normalize_surrah_share, sync_activity_employees
from smart_agri.core.services.activity_costing_support import calculate_identityless_casual_cost
# from smart_agri.core.services.costing import calculate_activity_cost # Decoupled to Async
from smart_agri.core.services.tree_inventory import TreeInventoryService
from .base import BaseService, ServiceResult

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

logger = logging.getLogger(__name__)


def _derive_activity_days_spent(explicit_days_spent, employees_payload):
    if explicit_days_spent not in (None, ""):
        return normalize_surrah_share(explicit_days_spent)

    if not employees_payload:
        return Decimal("0.00")

    normalized_entries = []
    for entry in employees_payload:
        surrah_value = entry.get("surrah_share")
        if surrah_value is None:
            surrah_value = entry.get("surra_units")
        normalized = normalize_surrah_share(surrah_value)
        if normalized > 0:
            normalized_entries.append(normalized)

    if not normalized_entries:
        return Decimal("0.00")

    return max(normalized_entries)


def _coerce_fk_primitive(value):
    if value in (None, "", 0, "0"):
        return None
    return value

class ActivityService(BaseService):
    """
    طبقة الخدمة المسؤولة عن العمليات الذرية للأنشطة.
    المصدر الوحيد للحقيقة (SSOT) لتغييرات الأنشطة لضمان تكامل البيانات.
    """

    @staticmethod
    def _normalize_aliases(data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(data)

        if "items" not in normalized and "items_payload" in normalized:
            normalized["items"] = normalized.get("items_payload")
        if "location_ids" not in normalized and "locations" in normalized:
            normalized["location_ids"] = normalized.get("locations")

        if "well_id" in normalized:
            coerced_well_id = _coerce_fk_primitive(normalized.get("well_id"))
            if "well_asset_id" not in normalized and coerced_well_id is not None:
                normalized["well_asset_id"] = coerced_well_id
            normalized.pop("well_id", None)

        fk_aliases = {
            "task": "task_id",
            "crop": "crop_id",
            "asset": "asset_id",
            "well_asset": "well_asset_id",
            "crop_variety": "crop_variety_id",
            "variety": "crop_variety_id",
            "product": "product_id",
            "tree_loss_reason": "tree_loss_reason_id",
            "crop_plan": "crop_plan_id",
        }
        for field_name, id_field_name in fk_aliases.items():
            value = normalized.get(field_name)
            if hasattr(value, "_meta"):
                continue
            coerced_value = _coerce_fk_primitive(value)
            if coerced_value is not None and id_field_name not in normalized:
                normalized[id_field_name] = coerced_value
            if field_name in normalized:
                normalized.pop(field_name, None)

        for id_field_name in set(fk_aliases.values()) | {"well_asset_id"}:
            if id_field_name not in normalized:
                continue
            if _coerce_fk_primitive(normalized.get(id_field_name)) is None:
                normalized.pop(id_field_name, None)

        return normalized

    @staticmethod
    @transaction.atomic
    def maintain_activity(user: Any, data: Dict[str, Any], activity_id: Optional[int] = None) -> ServiceResult[Activity]:
        """
        Refactored maintain_activity (Phase 5 - 100% Strict).
        Adds Parent Locking and Fiscal Period Validation.
        """
        from smart_agri.core.repositories import ActivityRepository
        from smart_agri.core.events import AgriEventBus
        from smart_agri.finance.services.core_finance import FinanceService
        
        repo = ActivityRepository()
        
        try:
            # 0. Preparation
            data = ActivityService._normalize_aliases(data)
            extension_data = ActivityService._extract_extension_data(data)
            has_items_key = 'items' in data
            employees_payload = data.pop('employees_payload', None)
            
            # [AGRI-GUARDIAN] Phase 1: Handle simple employee list from serializer
            simple_employees = data.pop('employees', None)
            default_surrah = data.pop('surrah_count', None) or Decimal('1.00')
            
            if simple_employees and not employees_payload:
                employees_payload = [
                    {'employee_id': emp_id, 'surrah_share': default_surrah}
                    for emp_id in simple_employees
                ]
            items_payload = data.pop('items', None)
            service_counts = data.pop('service_counts_payload', None)
            location_ids = data.pop('location_ids', None) # Multi-Location Support
            
            # 1. Persistence & Locking
            valid_fields = {f.name for f in Activity._meta.get_fields()}
            valid_fields.update(
                {
                    f.attname
                    for f in Activity._meta.get_fields()
                    if getattr(f, "attname", None)
                }
            )
            if "log_id" in data and "log" not in data:
                try:
                    data["log"] = DailyLog.objects.get(pk=data["log_id"])
                except DailyLog.DoesNotExist:
                    raise ValidationError("السجل اليومي المحدد غير موجود.")
            # Legacy/API alias normalization before model-field filtering.
            if "variety" in data and "crop_variety" not in data:
                data["crop_variety"] = data.get("variety")
            if "variety_id" in data and "crop_variety_id" not in data:
                data["crop_variety_id"] = data.get("variety_id")

            filtered_data = {k: v for k, v in data.items() if k in valid_fields}
            filtered_data["days_spent"] = _derive_activity_days_spent(
                filtered_data.get("days_spent"),
                employees_payload,
            )
            task_obj = filtered_data.get("task") or data.get("task")
            if not task_obj:
                task_id = filtered_data.get("task_id") or data.get("task_id")
                if task_id:
                    task_obj = Task.objects.filter(pk=task_id).first()
            if task_obj:
                filtered_data["task_contract_version"] = getattr(task_obj, "task_contract_version", 1)
                filtered_data["task_contract_snapshot"] = getattr(
                    task_obj,
                    "get_effective_contract",
                    lambda: {},
                )()

            is_new = activity_id is None
            
            # [CRITICAL 2%] Fiscal & Parent Locking Logic
            activity_log = data.get('log')
            log_id = activity_log.id if activity_log else data.get('log_id')
            activity_date = data.get('date') or data.get('activity_date')
            
            if is_new:
                parent_log = None
                if log_id:
                    # STRICT FIX: Lock the Parent Log to prevent closure during insertion
                    try:
                        parent_log = DailyLog.objects.select_for_update().get(pk=log_id)
                        if parent_log.status == 'closed':
                             raise ValidationError("لا يمكن إضافة نشاط لسجل يومي مغلق.")
                        if not activity_date:
                            activity_date = parent_log.log_date # Fallback to log date
                    except DailyLog.DoesNotExist:
                        raise ValidationError("السجل اليومي المحدد غير موجود.")
                ActivityService._resolve_crop_plan_for_new_activity(
                    payload=filtered_data,
                    parent_log=parent_log,
                )

                # [AGRI-GUARDIAN FIX] Auto-link to PlannedActivity for
                # task-level variance tracking (planned vs actual).
                ActivityService._link_planned_activity(
                    payload=filtered_data,
                    activity_date=activity_date or (parent_log.log_date if parent_log else None),
                )

                # Check Fiscal Period for the intended date
                if activity_date and hasattr(user, 'farm'): # Assuming user context carries farm or we fetch from log
                     # We need the farm. If log exists, get from log.
                     farm = parent_log.farm if 'parent_log' in locals() else None
                     if farm:
                        FinanceService.check_fiscal_period(activity_date, farm)

                # Defaults
                for cost_field in ['cost_materials', 'cost_labor', 'cost_machinery', 'cost_overhead', 'cost_wastage', 'cost_total']:
                    filtered_data.setdefault(cost_field, 0)

                # Legacy compatibility: if callers provide component costs only,
                # derive total cost deterministically.
                component_total = (
                    Decimal(str(filtered_data.get("cost_materials") or 0))
                    + Decimal(str(filtered_data.get("cost_labor") or 0))
                    + Decimal(str(filtered_data.get("cost_machinery") or 0))
                    + Decimal(str(filtered_data.get("cost_overhead") or 0))
                    + Decimal(str(filtered_data.get("cost_wastage") or 0))
                )
                if component_total > 0 and Decimal(str(filtered_data.get("cost_total") or 0)) <= 0:
                    filtered_data["cost_total"] = component_total

                # Legacy compatibility for historical tests/importers:
                # auto-attach a default loss reason when negative delta is provided.
                tree_delta = int(filtered_data.get("tree_count_delta") or 0)
                if tree_delta < 0 and not filtered_data.get("tree_loss_reason"):
                    default_reason, _ = TreeLossReason.objects.get_or_create(
                        code="LEGACY_UNSPECIFIED_LOSS",
                        defaults={
                            "name_en": "Legacy Unspecified Loss",
                            "name_ar": "فقد غير محدد (توافقي)",
                        },
                    )
                    filtered_data["tree_loss_reason"] = default_reason
                
                activity = repo.create(filtered_data, user)
            else:
                # Update existing
                activity = repo.get_by_id(activity_id, for_update=True)
                
                # Check Fiscal Period regarding the *Original* date AND the *New* date
                # Preventing moving an activity from a closed period to an open one, or vice versa
                if activity.crop_plan:
                     current_date = getattr(activity, 'activity_date', None)
                     FinanceService.check_fiscal_period(current_date, activity.crop_plan.farm)
                     if activity_date and current_date and activity_date != current_date:
                          FinanceService.check_fiscal_period(activity_date, activity.crop_plan.farm)

                activity = repo.update(activity, filtered_data, user)
            
            # Validation
            ActivityService._validate_business_rules(activity)
            activity = repo.save(activity)
            
            # [MULTI-LOCATION] Sync Activity Locations
            if location_ids is not None:
                from smart_agri.core.models.activity import ActivityLocation
                from smart_agri.core.models.planning import CropPlanLocation
                ActivityLocation.objects.filter(activity=activity).delete()
                
                if location_ids:
                    count = len(location_ids)
                    
                    # [AGRI-GUARDIAN] Area-Based Financial Allocation
                    plan_loc_areas = {}
                    if activity.crop_plan_id:
                        plan_locs = CropPlanLocation.objects.filter(
                            crop_plan_id=activity.crop_plan_id,
                            location_id__in=location_ids,
                            deleted_at__isnull=True
                        )
                        for pl in plan_locs:
                            if pl.assigned_area:
                                plan_loc_areas[pl.location_id] = Decimal(str(pl.assigned_area))
                    
                    total_area = sum(plan_loc_areas.get(lid, Decimal('0')) for lid in location_ids)
                    
                    loc_objects = []
                    for loc_id in location_ids:
                        if total_area > Decimal('0') and loc_id in plan_loc_areas:
                            pct = (plan_loc_areas[loc_id] / total_area * Decimal('100.00'))  # agri-guardian: decimal-safe
                        else:
                            pct = (Decimal('100.00') / Decimal(str(count)))  # agri-guardian: decimal-safe
                            
                        pct = pct.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        
                        loc_objects.append(
                            ActivityLocation(
                                activity=activity,
                                location_id=loc_id,
                                allocated_percentage=pct
                            )
                        )
                        
                    # Fix rounding errors (Sum Must be exactly 100.00)
                    total_pct = sum(loc.allocated_percentage for loc in loc_objects)
                    if total_pct != Decimal('100.00') and loc_objects:
                        diff = Decimal('100.00') - total_pct
                        loc_objects[0].allocated_percentage += diff
                    
                    ActivityLocation.objects.bulk_create(loc_objects)
            
            # 2. Extensions
            task = activity.task
            if task:
                ActivityService._handle_extensions(activity, task, extension_data)

            # 3. Sync Logic (Employees, Items, Coverage)
            if employees_payload:
                sync_activity_employees(activity, employees_payload)
            
            # [AGRI-GUARDIAN Phase 6] 2. Machinery Fuel Tracking via Smart Cards
            # Convert fuel_consumed directly into an ActivityItem (Material) for strict Inventory matching
            fuel_consumed_str = extension_data.get('fuel_consumed')
            if fuel_consumed_str:
                fuel_qty = Decimal(str(fuel_consumed_str))
                if fuel_qty > 0:
                    from smart_agri.inventory.models import Item
                    fuel_item = Item.objects.filter(group__iexact='Fuel').first()
                    if fuel_item:
                        items_payload = items_payload or []
                        already_has_fuel = any(
                            (str(i.get('item_id')) == str(fuel_item.id) or str(i.get('item')) == str(fuel_item.id)) 
                            for i in items_payload
                        )
                        if not already_has_fuel:
                            items_payload.append({
                                'item_id': fuel_item.id,
                                'qty': fuel_qty,
                                'uom': fuel_item.uom or 'L'
                            })
                            has_items_key = True

            if has_items_key:
                ActivityService._handle_items(activity, items_payload or [], user=user)
                
            if service_counts:
                 from smart_agri.core.services.tree_coverage import TreeCoverageService
                 TreeCoverageService().sync_service_coverages(
                     activity=activity,
                     entries=service_counts,
                     recorded_by=user,
                 )

            # [AGRI-GUARDIAN] Phase 3: Costing Engine
            from smart_agri.finance.services.costing_service import CostingService
            has_identityless_casual = activity.employee_details.filter(
                labor_type='CASUAL_BATCH',
                employee__isnull=True,
            ).exists()
            if has_identityless_casual:
                ActivityService._calculate_activity_cost_for_identityless_casual(activity)
            else:
                CostingService.calculate_activity_cost(activity)

            # [AGRI-GUARDIAN Phase 6] 1. Budget Governance (Hard Limits)
            # ActivityService._enforce_budget_limits(activity)

            # 4. Final Ledger Sync (Synchronous or Event-based)
            # Ensure costs are reflected immediately for UX, strictly checking logic
            FinanceService.sync_activity_ledger(activity, user)

            # 5. Event Bus
            AgriEventBus.publish(
                'activity_committed', 
                sender=ActivityService,
                activity_id=activity.id,
                is_new=is_new,
                user_id=user.id if user else None
            )

            return ServiceResult.ok(activity)

        except ValidationError as e:
            return ServiceResult.fail("خطأ في التحقق", errors=e.message_dict if hasattr(e, 'message_dict') else {"error": str(e)})
        except (OperationalError, IntegrityError, PermissionDenied, TypeError, ValueError) as e:
            logger.exception("فشل صيانة النشاط")
            return ServiceResult.fail(f"خطأ داخلي: {str(e)}")

    @staticmethod
    def _resolve_crop_plan_for_new_activity(payload: Dict[str, Any], parent_log: Optional[DailyLog]) -> None:
        """
        Enforce deterministic CropPlan linkage for activities that include crop + location.
        """
        if payload.get("crop_plan"):
            return

        crop = payload.get("crop")
        location_ids = payload.get("location_ids")
        if not crop or not location_ids:
            return

        farm_id = None
        if parent_log and parent_log.farm_id:
            farm_id = parent_log.farm_id
        elif payload.get("farm"):
            farm_id = getattr(payload.get("farm"), "id", payload.get("farm"))
        else:
            # Fallback - cannot infer single location's farm reliably for multiple locations
            pass

        if not farm_id:
            raise ValidationError(
                "Unable to resolve crop plan: activity is not linked to a valid farm (log/location/farm)."
            )

        from smart_agri.core.models.planning import CropPlan
        from smart_agri.core.constants import CropPlanStatus

        business_date_source = parent_log.log_date if parent_log else (
            payload.get("date")
            or payload.get("activity_date")
            or payload.get("log_date")
        )
        business_date = ActivityService._coerce_business_date(business_date_source)
        base_qs = CropPlan.objects.filter(
            farm_id=farm_id,
            crop_id=getattr(crop, "id", crop),
            status=CropPlanStatus.ACTIVE,
            deleted_at__isnull=True,
        )
        if business_date is not None:
            base_qs = base_qs.filter(
                start_date__lte=business_date,
                end_date__gte=business_date,
            )
        elif base_qs.count() > 1:
            raise ValidationError(
                "Unable to resolve crop plan deterministically: activity date is missing and multiple active plans match."
            )

        location_qs = base_qs.filter(locations__location_id__in=location_ids).distinct()
        if location_qs.exists():
            active_plan = location_qs.order_by("-start_date", "-id").first()
        elif base_qs.count() == 1:
            active_plan = base_qs.first()
        else:
            active_plan = None

        if not active_plan:
            raise ValidationError(
                "No matching active crop plan found (farm/crop/location/date). Activate a plan before saving the activity."
            )
        payload["crop_plan"] = active_plan

    @staticmethod
    def _coerce_business_date(raw_value) -> Optional[date]:
        if isinstance(raw_value, datetime):
            return raw_value.date()
        if isinstance(raw_value, date):
            return raw_value
        if isinstance(raw_value, str):
            try:
                return date.fromisoformat(raw_value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _link_planned_activity(payload: Dict[str, Any], activity_date) -> None:
        """
        [AGRI-GUARDIAN FIX] Auto-link Activity to its matching PlannedActivity.

        Matches by: 
        1. Exact Task + Activity Date falling within [expected_date_start, expected_date_end].
        2. Fallback to planned_date ≈ activity_date.
        
        Stores `planned_activity_id` in analytical_tags for task-level
        variance tracking without requiring a DB migration.
        """
        crop_plan = payload.get("crop_plan")
        task = payload.get("task")
        if not crop_plan or not task or not activity_date:
            return

        from smart_agri.core.models.planning import PlannedActivity
        from django.db.models import Q

        coerced_date = ActivityService._coerce_business_date(activity_date)
        if not coerced_date:
            return

        task_id = getattr(task, "id", task)

        # 1. Try Precision Window (expected_date_start -> expected_date_end)
        planned = PlannedActivity.objects.filter(
            crop_plan=crop_plan,
            task_id=task_id,
            expected_date_start__lte=coerced_date,
            expected_date_end__gte=coerced_date,
            deleted_at__isnull=True,
        ).first()

        # 2. Fallback to Legacy planned_date matching
        if not planned:
            planned = PlannedActivity.objects.filter(
                crop_plan=crop_plan,
                task_id=task_id,
                planned_date=coerced_date,
                deleted_at__isnull=True,
            ).first()

        # 3. Fallback to ±1 day tolerance (field work often spans days)
        if not planned:
            from datetime import timedelta
            planned = PlannedActivity.objects.filter(
                Q(planned_date__range=(coerced_date - timedelta(days=1), coerced_date + timedelta(days=1))) |
                Q(expected_date_start__range=(coerced_date - timedelta(days=1), coerced_date + timedelta(days=1))),
                crop_plan=crop_plan,
                task_id=task_id,
                deleted_at__isnull=True,
            ).order_by('planned_date').first()

        if planned:
            # Store in analytical_tags (non-breaking, no migration needed)
            tags = payload.get("analytical_tags") or {}
            tags["planned_activity_id"] = planned.id
            payload["analytical_tags"] = tags
            logger.info(
                "Linked Activity to PlannedActivity #%s (task=%s, date=%s)",
                planned.id, task_id, coerced_date,
            )

    @staticmethod
    def _extract_extension_data(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'harvest_quantity': data.pop('harvest_quantity', None),
            'harvest_uom': data.pop('harvest_uom', None),
            'batch_number': data.pop('batch_number', None),
            'product_id': data.pop('product_id', None),
            'water_volume': data.pop('water_volume', None),
            'water_uom': data.pop('water_uom', None),
            'well_reading': data.pop('well_reading', None),
            'well_asset_id': data.pop('well_asset_id', None),
            'machine_hours': data.pop('machine_hours', None),
            'fuel_consumed': data.pop('fuel_consumed', None),
            'start_meter': data.pop('start_meter', None),
            'end_meter': data.pop('end_meter', None),
            'fertilizer_quantity': data.pop('fertilizer_quantity', None),
            'planted_area': data.pop('planted_area', None),
            'planted_uom': data.pop('planted_uom', None),
            'planted_area_m2': data.pop('planted_area_m2', None),
            'is_solar_powered': data.pop('is_solar_powered', None),
            'diesel_qty': data.pop('diesel_qty', None),
        }

    @staticmethod
    def _validate_business_rules(activity: Activity) -> None:
        from smart_agri.core.constants import CropPlanStatus, AssetStatus
        if activity.crop_plan_id and activity.crop_plan.status in ['closed', CropPlanStatus.ARCHIVED, CropPlanStatus.COMPLETED]:
             raise ValidationError(f"لا يمكن تعديل نشاط لخطة محصول في حالة {activity.crop_plan.status}.")
        if activity.asset_id and getattr(activity.asset, 'status', AssetStatus.ACTIVE) != AssetStatus.ACTIVE:
             raise ValidationError(f"الأصل {activity.asset} غير نشط.")


    @staticmethod
    def _handle_extensions(activity: Activity, task: Any, data: Dict[str, Any]) -> None:
        """
        [Refactor Phase 4] Strategy Pattern for Extensions.
        Delegates to ExtensionProcessor.
        """
        from smart_agri.core.services.activity_extensions import ExtensionProcessor
        processor = ExtensionProcessor()
        processor.process_extensions(activity, data)


    @staticmethod
    @transaction.atomic
    def bulk_create_activities(user: Any, activities_data: List[Dict[str, Any]]) -> ServiceResult[List[Activity]]:
        """
        الإنشاء الجماعي المحسن (المرحلة 11).
        يكرر maintain_activity لكن يستعد لإدراجات دفتر الأستاذ الجماعية إذا لزم الأمر.
        """
        results = []
        for data in activities_data:
            res = ActivityService.maintain_activity(user, data)
            if not res.success:
                transaction.set_rollback(True)
                return ServiceResult.fail(f"Bulk failed at item: {res.message}", errors=res.errors)
            results.append(res.data)
        return ServiceResult.ok(results)

    @staticmethod
    def _handle_items(activity: Activity, items_payload: List[Dict[str, Any]], user: Any) -> None:
        """
        Syncs API payload to ActivityItem via ActivityItemService to ensure
        inventory and ledger consistency.
        Replaces existing items with new list.
        """
        from smart_agri.core.services.activity_item_service import ActivityItemService
        ActivityItemService.batch_process_items(
            activity=activity, 
            items_payload=items_payload, 
            user=user, 
            replace_existing=True
        )

    @staticmethod
    def _sync_employees(activity: Activity, employees_payload: List[Dict[str, Any]]) -> None:
        sync_activity_employees(activity, employees_payload)

    @staticmethod
    def _normalize_surrah_share(surrah_value) -> Decimal:
        return normalize_surrah_share(surrah_value)

    @staticmethod
    def _calculate_activity_cost_for_identityless_casual(activity: Activity) -> None:
        calculate_identityless_casual_cost(activity)

    @staticmethod
    @transaction.atomic
    def delete_activity(user: Any, activity: Activity) -> ServiceResult[bool]:
        """يحذف نشاطاً بأمان مع عكس القيود المالية باستخدام Event Bus."""
        from smart_agri.core.events import EventBus, ActivityDeleted
        from smart_agri.core.repositories import ActivityRepository
        
        if FinancialLedger.objects.filter(activity=activity).exists():
            return ServiceResult.fail("لا يمكن حذف النشاط مرتبط بقيد مالي مرحّل.")
        if StockMovement.objects.filter(ref_id=str(activity.id)).exists():
            return ServiceResult.fail("لا يمكن حذف النشاط المرتبط بحركة مخزون مؤتمتة.")
        
        try:
            # 1. Publish Deletion Event (Triggering Reversals)
            # Before actual delete so we have access to data if needed (soft delete retains it anyway)
            # But strict reversal usually happens before.
            EventBus.publish(ActivityDeleted(activity, user))

            # 2. Repository Delete
            repo = ActivityRepository()
            repo.delete(activity)
            
            return ServiceResult.ok(True)
        except (ValidationError, OperationalError, IntegrityError) as e:
            logger.exception("فشل الحذف")
            return ServiceResult.fail(f"فشل الحذف: {str(e)}")
