"""
Frictionless DailyLog Execution Service — بوابة التسجيل المُبسَّط.

Accepts ONLY technical inputs from field staff:
  - activity_name, workers_count, shift_hours, machine_hours
  - dipstick_start_liters, dipstick_end_liters (diesel reading)
  - farm_id, supervisor_id, log_date

ALL financial calculations are computed server-side from LaborRate / MachineRate.
Deviations are routed through ShadowVarianceEngine (shadow or block based on mode).

Hard blocks enforced (regardless of strict_erp_mode):
- No IoT/sensor data (AGENTS.md § No IoT Policy)
- farm_id is mandatory (AGENTS.md § Farm Tenant Isolation)
"""

from decimal import Decimal, ROUND_HALF_UP
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.settings import MachineRate, LaborRate
from smart_agri.core.services.shadow_variance_engine import ShadowVarianceEngine

import logging

logger = logging.getLogger(__name__)

ZERO = Decimal('0.0000')
FOUR_DP = Decimal('0.0001')
SURRA_HOURS = Decimal('8.0')


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(FOUR_DP, rounding=ROUND_HALF_UP)


def _decimal_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= ZERO:
        raise ValidationError("القسمة على صفر غير مسموحة في حسابات التنفيذ اليومي.")
    return (numerator / denominator).quantize(FOUR_DP, rounding=ROUND_HALF_UP)  # agri-guardian: decimal-safe


class FrictionlessDailyLogService:
    """
    Service layer for simplified daily log entry.

    Separates data entry (technical) from financial enforcement (server-side).
    All mutations use transaction.atomic() per AGENTS.md doctrine.
    """

    @staticmethod
    @transaction.atomic
    def process_technical_log(
        farm,
        log_date,
        activity_name: str,
        workers_count: int = 0,
        shift_hours: Decimal = ZERO,
        machine_asset=None,
        machine_hours: Decimal = ZERO,
        dipstick_start_liters: Decimal = ZERO,
        dipstick_end_liters: Decimal = ZERO,
        supervisor=None,
        notes: str = "",
        crop_plan=None,
        created_by=None,
    ) -> dict:
        """
        بوابة التسجيل اليومي المُبسَّط (Frictionless Entry).

        Args:
            farm: Farm instance (tenant scope)
            log_date: Date of the log entry
            activity_name: Name of the activity performed
            workers_count: Number of workers
            shift_hours: Total shift hours (Decimal)
            machine_asset: Asset instance (optional, for machine-based work)
            machine_hours: Machine operation hours (Decimal)
            dipstick_start_liters: Fuel level at shift start (Decimal)
            dipstick_end_liters: Fuel level at shift end (Decimal)
            supervisor: Supervisor instance (optional)
            notes: Free-text notes
            created_by: User performing the entry

        Returns:
            dict with daily_log_id, labor_cost, machine_cost, diesel_consumed,
            total_cost, variance_result, diesel_result

        Raises:
            ValidationError for data integrity violations
        """
        # ── 1. Validate dipstick readings ────────────────────────────
        if dipstick_start_liters < ZERO or dipstick_end_liters < ZERO:
            raise ValidationError(
                "🔴 [FORENSIC BLOCK] قراءة الديبستيك لا يمكن أن تكون سالبة."
            )
        if dipstick_start_liters > ZERO and dipstick_end_liters > dipstick_start_liters:
            raise ValidationError(
                "🔴 [FORENSIC BLOCK] قراءة نهاية الديبستيك أعلى من البداية. "
                "الديزل لا يتزايد أثناء التشغيل."
            )

        # ── 2. Compute labor cost from LaborRate ─────────────────────
        labor_cost = ZERO
        if workers_count > 0 and shift_hours > ZERO:
            labor_rate = LaborRate.objects.filter(
                farm=farm, deleted_at__isnull=True,
            ).order_by('-effective_date').first()

            if labor_rate:
                # [AGRI-GUARDIAN § Axis-5] Surra standard: favor daily_rate over hours
                if labor_rate.daily_rate and labor_rate.daily_rate > ZERO:
                    # Assumes 8 hours = 1 Surra (shift)
                    shifts = _decimal_ratio(shift_hours, SURRA_HOURS) # agri-guardian: decimal-safe
                    if shifts == ZERO: shifts = Decimal('1.0') # Minimum 1 shift if workers are present
                    labor_cost = (
                        Decimal(str(workers_count))
                        * shifts
                        * labor_rate.daily_rate
                    ).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
                else:
                    labor_cost = (
                        Decimal(str(workers_count))
                        * shift_hours
                        * labor_rate.cost_per_hour
                    ).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

        # ── 3. Compute machine cost from MachineRate ─────────────────
        machine_cost = ZERO
        fuel_rate = ZERO
        if machine_asset and machine_hours > ZERO:
            try:
                machine_rate = MachineRate.objects.get(
                    asset=machine_asset, deleted_at__isnull=True,
                )
                machine_cost = (
                    machine_hours * machine_rate.cost_per_hour
                ).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
                fuel_rate = machine_rate.fuel_consumption_rate or ZERO
            except MachineRate.DoesNotExist:
                logger.warning(
                    "No MachineRate found for asset %s — cost skipped",
                    machine_asset,
                )

        # ── 4. Compute diesel consumed from dipstick ─────────────────
        diesel_consumed = ZERO
        if dipstick_start_liters > ZERO:
            diesel_consumed = (
                dipstick_start_liters - dipstick_end_liters
            ).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

        # ── 5. Total cost ────────────────────────────────────────────
        total_cost = (labor_cost + machine_cost).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )

        # ── 6. Create DailyLog ───────────────────────────────────────
        daily_log = DailyLog(
            farm=farm,
            supervisor=supervisor,
            log_date=log_date,
            notes=notes or f"سجل مُبسَّط: {activity_name}",
            observation_data={
                "activity_name": activity_name,
                "workers_count": workers_count,
                "shift_hours": str(shift_hours),
                "machine_hours": str(machine_hours),
                "dipstick_start": str(dipstick_start_liters),
                "dipstick_end": str(dipstick_end_liters),
                "diesel_consumed": str(diesel_consumed),
                "labor_cost": str(labor_cost),
                "machine_cost": str(machine_cost),
                "total_cost": str(total_cost),
                "entry_type": "FRICTIONLESS",
            },
            created_by=created_by,
        )
        daily_log.full_clean()
        daily_log.save()

        # ── 7. Diesel audit via ShadowVarianceEngine ─────────────────
        diesel_result = "SKIPPED_NO_MACHINE"
        if machine_asset and fuel_rate > ZERO and machine_hours > ZERO:
            expected_liters = (machine_hours * fuel_rate).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            diesel_result = ShadowVarianceEngine.audit_diesel_consumption(
                farm=farm,
                daily_log=daily_log,
                asset_name=str(machine_asset),
                actual_liters=diesel_consumed,
                expected_liters=expected_liters,
                machine_hours=machine_hours,
            )

        # ── 8. Budget variance audit (Task-Level) ─────────────────────
        # [AGRI-GUARDIAN FIX] Resolve planned cost from PlannedActivity
        # instead of the arbitrary budget_total/100 proxy.
        variance_result = "SKIPPED_NO_PLAN"
        if crop_plan and crop_plan.budget_total > ZERO:
            planned_cost = _resolve_planned_cost(
                crop_plan=crop_plan,
                activity_name=activity_name,
                log_date=log_date,
            )
            variance_result = ShadowVarianceEngine.audit_execution_cost(
                farm=farm,
                daily_log=daily_log,
                activity_name=activity_name,
                actual_cost=total_cost,
                planned_cost=planned_cost,
            )

        # ── 9. Shadow Ledger Entries (SIMPLE Mode Forensic) ───────────
        # [AGRI-GUARDIAN FIX] Create FinancialLedger shadow rows so
        # SIMPLE mode preserves forensic data integrity per HYBRID_MODE §4.
        from smart_agri.finance.services.core_finance import FinanceService
        from smart_agri.core.models.activity import Activity

        shadow_activity = Activity.objects.filter(
            log=daily_log,
        ).order_by('-id').first()

        if shadow_activity:
            FinanceService.sync_activity_ledger(shadow_activity, created_by)
        else:
            # Shadow accounting is a hard integrity requirement in SIMPLE mode.
            from smart_agri.finance.models import FinancialLedger
            shadow_idemp_key = f'shadow-dailylog-{daily_log.id}'
            if not FinancialLedger.objects.filter(idempotency_key=shadow_idemp_key).exists():
                FinancialLedger(
                    farm=farm,
                    account_code=FinancialLedger.ACCOUNT_WIP,
                    debit=total_cost,
                    credit=Decimal('0.0000'),
                    description=f'Shadow entry — DailyLog #{daily_log.id} ({activity_name})',
                    created_by=created_by,
                    idempotency_key=shadow_idemp_key,
                    analytical_tags={
                        'source': 'frictionless_daily_log',
                        'mode': 'SIMPLE',
                        'daily_log_id': daily_log.id,
                    },
                ).save()
            logger.info(
                "Shadow Ledger: Direct entry for log %s (no Activity yet).",
                daily_log.id,
            )

        # ── 10. Update fuel alert status on the DailyLog ─────────────
        if diesel_result == "SHADOW_ALERT_CREATED":
            daily_log.fuel_alert_status = DailyLog.FUEL_ALERT_STATUS_WARNING
            daily_log.fuel_alert_note = (
                f"تنبيه ديزل: استهلاك {diesel_consumed} لتر"
            )
            daily_log.save(update_fields=[
                'fuel_alert_status', 'fuel_alert_note',
            ])

        logger.info(
            "Frictionless log created: farm=%s, activity=%s, "
            "labor=%.4f, machine=%.4f, diesel=%.4f L",
            farm, activity_name, labor_cost, machine_cost, diesel_consumed,
        )

        return {
            "daily_log_id": daily_log.id,
            "labor_cost": str(labor_cost),
            "machine_cost": str(machine_cost),
            "diesel_consumed": str(diesel_consumed),
            "total_cost": str(total_cost),
            "variance_result": variance_result,
            "diesel_result": diesel_result,
        }


def _resolve_planned_cost(crop_plan, activity_name: str, log_date) -> Decimal:
    """
    [AGRI-GUARDIAN §Axis-14] Resolve real planned cost from PlannedActivity.

    Priority:
    1. Match PlannedActivity by task name + date within the CropPlan.
    2. If PlannedMaterials exist, sum their planned costs.
    3. Fallback: daily budget slice = budget_total / plan_duration_days.
    """
    from smart_agri.core.models.planning import PlannedActivity, PlannedMaterial

    FOUR_DP = Decimal('0.0001')

    # 1. Try exact PlannedActivity match (task name + date)
    planned = PlannedActivity.objects.filter(
        crop_plan=crop_plan,
        task__name__icontains=activity_name,
        planned_date=log_date,
        deleted_at__isnull=True,
    ).first()

    if planned:
        # Sum planned materials for this planned activity
        material_cost = PlannedMaterial.objects.filter(
            planned_activity=planned,
            deleted_at__isnull=True,
        ).aggregate(
            total=models.Sum(
                models.F('planned_qty') * models.F('estimated_unit_price')
            )
        ).get('total') or ZERO

        # Add estimated labor (hours × farm labor rate)
        labor_estimate = ZERO
        if planned.estimated_hours and planned.estimated_hours > ZERO:
            rate = LaborRate.objects.filter(
                farm=crop_plan.farm,
                deleted_at__isnull=True,
            ).order_by('-effective_date').first()
            if rate and rate.daily_rate and rate.daily_rate > ZERO:
                shifts = _decimal_ratio(planned.estimated_hours, SURRA_HOURS)
                labor_estimate = (shifts * rate.daily_rate).quantize(FOUR_DP)

        total_planned = (material_cost + labor_estimate).quantize(FOUR_DP)
        if total_planned > ZERO:
            return total_planned

    # 2. Fallback: daily slice of total budget
    duration_days = Decimal('1')
    if crop_plan.start_date and crop_plan.end_date:
        delta = (crop_plan.end_date - crop_plan.start_date).days
        if delta > 0:
            duration_days = Decimal(str(delta))

    return _decimal_ratio(crop_plan.budget_total, duration_days)
