from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction, OperationalError
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Sum
from smart_agri.core.models import Activity, ActivityHarvest
from smart_agri.finance.models import FinancialLedger
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.core.services.zakat_policy import (
    resolve_zakat_rate,
    resolve_zakat_policy_for_harvest,
    normalize_business_date,
)
from smart_agri.inventory.models import StockMovement
import logging

logger = logging.getLogger(__name__)

# [AGRI-GUARDIAN §8.I] Bio-Constraint Constants
YIELD_ALERT_THRESHOLD = Decimal("1.2")  # 120% of max biological limit triggers advisory



class HarvestService:
    """
    Harvest Service.
    Bridge between Production (Field) and Inventory (Store).
    """
    COST_PRECISION = Decimal("0.0001")
    VALUE_PRECISION = Decimal("0.0001")

    @staticmethod
    def calculate_zakat_due(quantity, zakat_rule: str) -> Decimal:
        """
        [AGRI-GUARDIAN] ZAKAT DOCTRINE
        Enforce 5% for Irrigated (cost-heavy) vs 10% for Rain-fed.
        """
        quantity_dec = Decimal(str(quantity))

        rate = HarvestService._resolve_zakat_rate_from_rule(zakat_rule)
        zakat_amount = quantity_dec * rate
        return zakat_amount.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _resolve_zakat_rate_from_rule(zakat_rule: str) -> Decimal:
        return resolve_zakat_rate(zakat_rule)

    @staticmethod
    @transaction.atomic
    def process_harvest(activity: Activity, user, *, idempotency_key=None):
        """
        Processes the financial and physical impact of a Harvest Activity.
        Should be called when Activity is confirmed/closed.

        [AGENTS.md Compliance]
        - Axis 2: Idempotency Key enforcement
        - Axis 3: Fiscal Period Gate
        - Axis 7: AuditLog
        - Axis 9: Zakat Quarantine in enforce mode
        """
        # 1. Validation
        if not hasattr(activity, 'harvest_details'):
             # Not a harvest activity
             return

        details = activity.harvest_details
        gross_qty = details.harvest_quantity
        if gross_qty is None or gross_qty <= 0:
             return

        # [Axis 2] Idempotency Key enforcement (full)
        if idempotency_key:
            if FinancialLedger.objects.filter(idempotency_key=idempotency_key).exists():
                logger.info("Harvest %s: idempotency_key=%s already processed; replay skipped.", activity.pk, idempotency_key)
                return

        # Legacy idempotency guard for weak network retries:
        if FinancialLedger.objects.filter(
            activity=activity,
            account_code=FinancialLedger.ACCOUNT_ZAKAT_PAYABLE,
        ).exists():
            logger.info("Harvest %s already processed for zakat liability; replay skipped.", activity.pk)
            return

        # [Axis 3] Fiscal Period Gate — reject harvest in hard-closed period
        try:
            from smart_agri.finance.models import FiscalPeriod
            harvest_date = getattr(details, 'harvest_date', None) or getattr(activity, 'activity_date', None)
            farm_id = getattr(activity, 'farm_id', None) or getattr(getattr(activity, 'log', None), 'farm_id', None)
            closed_period = FiscalPeriod.objects.filter(
                start_date__lte=harvest_date,
                end_date__gte=harvest_date,
                status='hard-close',
            ).first()
            if closed_period:
                raise ValidationError(
                    f"[Axis 3] الفترة المالية مقفلة (hard-close) للتاريخ {harvest_date}. "
                    "لا يمكن تسجيل حصاد في فترة مغلقة."
                )
        except ImportError:
            pass  # FiscalPeriod not available

        # [Axis 15] Dual-Mode Zakat Toggle
        farm_instance = getattr(activity, 'farm', None)
        farm_instance_id = getattr(farm_instance, 'id', None)
        if not isinstance(farm_instance_id, int):
            farm_instance = getattr(getattr(activity, 'log', None), 'farm', None)
            farm_instance_id = getattr(farm_instance, 'id', None)
        is_zakat_enabled = True
        farm_settings = None
        try:
            from smart_agri.core.models.settings import FarmSettings
            if isinstance(farm_instance_id, int):
                farm_settings = FarmSettings.objects.filter(farm_id=farm_instance_id).first()
            if farm_settings:
                is_zakat_enabled = farm_settings.enable_zakat
        except (ImportError, OperationalError):
            pass

        # [Axis 9] Zakat Quarantine — enforce mode rejects missing policy
        try:
            from django.conf import settings
            zakat_mode = getattr(settings, 'LOCATION_ZAKAT_POLICY_V2_MODE', 'shadow')
            if is_zakat_enabled and zakat_mode in ('enforce', 'full'):
                from smart_agri.core.services.zakat_policy import resolve_location_zakat_rate
                location = activity.location
                if location:
                    harvest_date = getattr(details, 'harvest_date', None) or getattr(activity, 'activity_date', None)
                    rate = resolve_location_zakat_rate(location.id, harvest_date)
                    if rate is None:
                        raise ValidationError(
                            f"[Axis 9] لا توجد سياسة ري/زكاة فعّالة للموقع '{location.name}' "
                            f"بتاريخ {harvest_date}. مطلوب تعيين LocationIrrigationPolicy "
                            "قبل تسجيل الحصاد (وضع enforce)."
                        )
        except ImportError:
            pass

        # 2. Resolve Product -> Item
        # ActivityHarvest has 'product_id' (BigInt) or we use 'lot'. 
        # Models show: product_id = BigIntegerField. 
        # We need the CropProduct model to find the Item.
        from smart_agri.core.models import CropProduct
        
        product = None
        if details.product_id:
            product = CropProduct.objects.filter(pk=details.product_id).first()
        elif getattr(activity, 'product', None):
            product = activity.product
            
        if not product:
            logger.warning(f"Harvest {activity.pk}: No product linked. Cannot update inventory.")
            return
            
        target_item = product.item
        if not target_item:
             logger.warning(f"Harvest {activity.pk}: Product {product.name} has no Inventory Item linked.")
             return

        # [AGRI-GUARDIAN §8.I] Bio-Constraint Yield Alert (Advisory Mode per §10 Yemen Context).
        # Check if the harvest yield per hectare exceeds the crop's biological max.
        # This is a WARNING, not a block — local agricultural expertise may know better.
        crop = product.crop if product else None
        crop_plan = activity.crop_plan
        if crop and crop_plan and crop.max_yield_per_ha and crop.max_yield_per_ha > 0:
            plan_area = crop_plan.area or Decimal("1")
            plan_area_val = Decimal(str(getattr(plan_area, "value", plan_area)))
            yield_per_ha = (gross_qty / plan_area_val).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)  # agri-guardian: decimal-safe
            max_allowed = crop.max_yield_per_ha * YIELD_ALERT_THRESHOLD

            if yield_per_ha > max_allowed:
                alert_msg = (
                    f"[AGRI-GUARDIAN §8.I] تنبيه حيوي: الإنتاجية الفعلية "
                    f"({yield_per_ha} طن/هكتار) تتجاوز الحد الأقصى البيولوجي "
                    f"({crop.max_yield_per_ha} × 120% = {max_allowed} طن/هكتار) "
                    f"للمحصول {crop.name}. النشاط: {activity.pk}"
                )
                logger.warning(alert_msg)

                # Record in AuditLog for traceability
                try:
                    from smart_agri.core.services.sensitive_audit import log_sensitive_mutation
                    log_sensitive_mutation(
                        actor=user,
                        action="bio_constraint_alert",
                        model_name="ActivityHarvest",
                        object_id=activity.pk,
                        reason=alert_msg,
                        old_value={"max_yield_per_ha": str(crop.max_yield_per_ha)},
                        new_value={"actual_yield_per_ha": str(yield_per_ha)},
                        farm_id=activity.log.farm_id,
                        context={"source": "harvest_service_bio_check"},
                    )
                except (ValidationError, ObjectDoesNotExist, OperationalError) as e:
                    logger.warning("Bio constraint audit log failed: %s", e)

        # 3. Valuation (Costing) (Strict Precision)
        from django.conf import settings 

        unit_cost = HarvestService._resolve_unit_cost(activity, gross_qty, product)
        if unit_cost <= 0:
            unit_cost = Decimal("0")

        # [AGRI-GUARDIAN Phase 14] Sharecropping Pre-Zakat Split
        sharecropping_enabled = False
        if farm_settings:
            sharecropping_enabled = farm_settings.enable_sharecropping

        farm_qty = gross_qty
        partner_qty = Decimal("0")
        partner_contract = None

        if sharecropping_enabled and crop_plan:
            try:
                from smart_agri.core.models.partnerships import SharecroppingContract
                partner_contract = SharecroppingContract.objects.filter(
                    farm=crop_plan.farm,
                    crop=crop_plan.crop,
                    season=crop_plan.season,
                    is_active=True
                ).first()
                if partner_contract:
                    farm_qty = (gross_qty * partner_contract.institution_percentage).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
                    partner_qty = gross_qty - farm_qty
                    logger.info(f"Sharecropping Split Applied: Farm={farm_qty}, Partner={partner_qty}")
            except (ImportError, ValidationError, ObjectDoesNotExist, TypeError, ValueError) as e:
                logger.warning(f"Failed to apply sharecropping split: {e}")

        if not is_zakat_enabled:
            zakat_rate = Decimal("0")
            zakat_qty = Decimal("0")
            net_qty = farm_qty
        else:
            business_dt = normalize_business_date(
                activity.device_timestamp or getattr(activity.log, "device_timestamp", None) or activity.log.log_date
            )
            if activity.location_id is None:
                raise ValidationError("Harvest location is required for zakat policy resolution.")
            location_policy = resolve_zakat_policy_for_harvest(activity.location, business_dt)
            active_rule = (
                location_policy.zakat_rule
                if location_policy is not None
                else getattr(activity.log.farm, "zakat_rule", None)
            )
            zakat_rate = HarvestService._resolve_zakat_rate_from_rule(active_rule)
            # Apply Zakat to the Farm's portion only
            zakat_qty = HarvestService.calculate_zakat_due(farm_qty, active_rule)
            net_qty = farm_qty - zakat_qty
            if net_qty < 0:
                 raise ValidationError("Harvest net quantity must not be less than zero after zakat deduction.")

        # Inventory recognizes full farm physical harvest (zakat is liability). Partner is bypassed or handed over physically.
        inventory_qty = farm_qty

        # Recalculate total strictly based on the rounded unit cost
        total_value = (inventory_qty * unit_cost).quantize(HarvestService.VALUE_PRECISION, rounding=ROUND_HALF_UP)
        zakat_value = (zakat_qty * unit_cost).quantize(HarvestService.VALUE_PRECISION, rounding=ROUND_HALF_UP)
        
        # 4. Inventory GRN (Add to Stock)
        # Guard against legacy signal path that already inserted harvest stock movement.
        signal_stock_exists = StockMovement.objects.filter(
            farm=activity.log.farm,
            item=target_item,
            ref_type="harvest_activity",
            ref_id=str(activity.pk),
            deleted_at__isnull=True,
        ).exists()
        if not signal_stock_exists:
            InventoryService.process_grn(
                farm=activity.log.farm,
                item=target_item,
                location=activity.location,
                qty=inventory_qty,
                unit_cost=unit_cost,
                ref_id=f"HARVEST-{activity.pk}",
                batch_number=details.batch_number,
                actor_user=user,
            )
        
        # 5. Financial Ledger (Asset Recognition)
        # Fetch Farm's currency or System Default
        currency_code = getattr(activity.crop_plan, 'currency', getattr(settings, 'DEFAULT_CURRENCY', 'YER'))
        
        if total_value > 0:
            crop_plan = getattr(activity, 'crop_plan', None)
            common_kwargs = dict(
                activity=activity,
                created_by=user,
                currency=currency_code,
                farm=getattr(activity, 'farm', None) or (crop_plan.farm if crop_plan else None),
                crop_plan=crop_plan,
                cost_center=getattr(activity, 'cost_center', None),
            )
            
            FinancialLedger.objects.create(
                account_code=FinancialLedger.ACCOUNT_INVENTORY_ASSET,
                debit=total_value,
                credit=0,
                description=f"أصل محصول حصاد: {product.name} ({inventory_qty}{details.uom})",
                **common_kwargs
            )
            FinancialLedger.objects.create(
                account_code=FinancialLedger.ACCOUNT_WIP, # or Gain
                debit=0,
                credit=total_value,
                description=f"قيمة الإنتاج (صافي من الزكاة): {activity.pk}",
                **common_kwargs
            )
            if zakat_value > 0:
                FinancialLedger.objects.create(
                    account_code=FinancialLedger.ACCOUNT_ZAKAT_EXPENSE,
                    debit=zakat_value,
                    credit=0,
                    description=f"مصروف زكاة: حصاد {activity.pk} بنسبة {zakat_rate}",
                    **common_kwargs
                )
                FinancialLedger.objects.create(
                    account_code=FinancialLedger.ACCOUNT_ZAKAT_PAYABLE,
                    debit=0,
                    credit=zakat_value,
                    description=f"زكاة مستحقة الدفع: حصاد {activity.pk}",
                    **common_kwargs
                )

        # 6. Traceability Record (HarvestLot) - Source for Harvest Catalog
        # [Agri-Guardian] Truth Protocol: Operational Log MUST reflect in Catalog.
        from smart_agri.core.models import HarvestLot
        
        HarvestLot.objects.create(
            farm=activity.log.farm,
            crop=product.crop,
            crop_plan=activity.crop_plan,
            product=product,
            location=activity.location,
            harvest_date=activity.log.log_date,
            quantity=inventory_qty,
            uom=details.uom or product.uom,
            grade=getattr(details, 'grade', 'First'), # Default to First if not specified
        )
            
        # [Axis 7] AuditLog — mandatory forensic trail for harvest mutation
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='HARVEST',
            model='Activity',
            object_id=str(activity.pk),
            actor=user,
            new_payload={
                'gross_qty': str(gross_qty),
                'net_qty': str(net_qty),
                'zakat_qty': str(zakat_qty),
                'zakat_value': str(zakat_value) if zakat_value else '0',
                'unit_cost': str(unit_cost),
                'product': product.name,
                'crop_plan_id': getattr(activity.crop_plan, 'id', None),
                'farm_id': getattr(activity, 'farm_id', None) or getattr(getattr(activity, 'log', None), 'farm_id', None),
            },
        )

        logger.info(
            "Harvest Processed: %s -> Gross %s, Zakat %s, Net %s %s @ %s",
            activity.pk,
            gross_qty,
            zakat_qty,
            net_qty,
            product.name,
            unit_cost,
        )

    @staticmethod
    def _resolve_unit_cost(activity: Activity, gross_qty: Decimal, product) -> Decimal:
        if gross_qty <= 0:
            return Decimal("0")

        plan = activity.crop_plan
        shared_cost = HarvestService._sum_crop_plan_cost(activity, plan)
        if plan and shared_cost > 0:
            expected = plan.expected_yield or gross_qty
            denominator = expected if expected > 0 else gross_qty
            denominator_val = Decimal(str(getattr(denominator, "value", denominator)))
            return (shared_cost / denominator_val).quantize(HarvestService.COST_PRECISION, rounding=ROUND_HALF_UP)  # agri-guardian: decimal-safe

        if activity.cost_total and activity.cost_total > 0:
            gross_qty_val = Decimal(str(getattr(gross_qty, "value", gross_qty)))
            return (activity.cost_total / gross_qty_val).quantize(HarvestService.COST_PRECISION, rounding=ROUND_HALF_UP)  # agri-guardian: decimal-safe

        if product and product.reference_price:
            return product.reference_price

        return Decimal("0")

    @staticmethod
    def _sum_crop_plan_cost(activity: Activity, crop_plan):
        if not crop_plan:
            return Decimal("0")
        from smart_agri.core.models.activity import ActivityCostSnapshot

        snapshot_total = (
            ActivityCostSnapshot.objects.filter(
                crop_plan=crop_plan, activity__log__farm_id=activity.log.farm_id
            )
            .aggregate(total=Sum('cost_total'))
            .get('total') or Decimal("0")
        )
        if snapshot_total > 0:
            return snapshot_total

        from smart_agri.core.models import Activity as ActivityModel
        activity_total = (
            ActivityModel.objects.filter(
                crop_plan=crop_plan,
                log__farm_id=activity.log.farm_id,
                deleted_at__isnull=True,
            )
            .aggregate(total=Sum('cost_total'))
            .get('total') or Decimal("0")
        )
        return activity_total
