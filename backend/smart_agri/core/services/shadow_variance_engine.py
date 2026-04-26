"""
Shadow Variance Engine — القلب النابض للنظام الهجين (Hybrid ERP Engine).

Responsibilities:
1. Receive actual vs planned cost for any farm operation.
2. Check SystemSettings.strict_erp_mode toggle.
3. If strict → raise ValidationError (hard block, no save).
4. If shadow → create VarianceAlert silently, allow operation to proceed.

Design decisions:
- Pure service layer (no Django views/models defined here).
- All arithmetic uses Decimal per AGENTS.md § Data Types.
- Division-by-zero protected (skip if planned_cost ≤ 0).
- Returns a string status code so callers can branch if needed.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.core.exceptions import ValidationError

from smart_agri.core.models.settings import FarmSettings, SystemSettings
from smart_agri.core.models.report import VarianceAlert

import logging

logger = logging.getLogger(__name__)


class ShadowVarianceEngine:
    """
    مسؤول عن تدقيق كافة العمليات التشغيلية خلف الكواليس دون إعاقة تجربة المزارع.

    Usage::

        from smart_agri.core.services.shadow_variance_engine import ShadowVarianceEngine

        result = ShadowVarianceEngine.audit_execution_cost(
            farm=farm_instance,
            daily_log=log_instance,          # optional
            activity_name="حراثة وتسوية",
            actual_cost=Decimal('45000.0000'),
            planned_cost=Decimal('35000.0000'),
            category=VarianceAlert.CATEGORY_BUDGET_OVERRUN,
        )
        # result in: "AUDIT_PASSED_OK", "SHADOW_ALERT_CREATED", "SKIPPED_NO_PLAN"
    """

    @staticmethod
    def _is_strict_mode(farm) -> bool:
        farm_id = getattr(farm, "id", None) if farm is not None else None
        if not isinstance(farm_id, int):
            return False
        farm_settings = FarmSettings.objects.filter(farm_id=farm_id).first()
        if not farm_settings:
            return False
        return farm_settings.mode == FarmSettings.MODE_STRICT

    @staticmethod
    def audit_execution_cost(
        farm,
        activity_name: str,
        actual_cost: Decimal,
        planned_cost: Decimal,
        daily_log=None,
        category: str = VarianceAlert.CATEGORY_BUDGET_OVERRUN,
    ) -> str:
        """
        Core audit function — evaluates a cost entry against the plan.

        Returns:
            "SKIPPED_NO_PLAN"       — planned_cost is zero or negative, nothing to compare.
            "AUDIT_PASSED_OK"       — actual is within allowed variance threshold.
            "SHADOW_ALERT_CREATED"  — over threshold in shadow mode; VarianceAlert created.

        Raises:
            ValidationError — over threshold in strict_erp_mode=True (hard block).
        """
        settings = SystemSettings.get_settings()

        # Guard: no baseline to compare against
        if planned_cost <= Decimal('0.0000'):
            logger.info(
                "ShadowVarianceEngine: Skipping audit for '%s' — "
                "no baseline planned cost (planned_cost=%s).",
                activity_name, planned_cost,
            )
            return "SKIPPED_NO_PLAN"

        # Compute variance
        variance_amount = (actual_cost - planned_cost).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )

        # Only trigger on overruns (actual > planned)
        if variance_amount <= Decimal('0.0000'):
            return "AUDIT_PASSED_OK"

        # Compute percentage
        variance_percentage = (
            (variance_amount / planned_cost) * Decimal('100.00') # agri-guardian: decimal-safe
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Check against allowed threshold
        if variance_percentage <= settings.allowed_variance_percentage:
            return "AUDIT_PASSED_OK"

        # --- Threshold exceeded ---

        if ShadowVarianceEngine._is_strict_mode(farm):
            # STRICT MODE: Hard block — raise error, prevent save
            error_msg = (
                f"🔴 [ERP BLOCK] تجاوز الميزانية المعتمدة لعملية ({activity_name}). "
                f"المخطط: {planned_cost}، الفعلي: {actual_cost}. "
                f"نسبة التجاوز: {variance_percentage}%. "
                "يرجى التواصل مع إدارة القطاع لطلب تعزيز مالي مسبق."
            )
            raise ValidationError(error_msg)

        # SHADOW MODE: Allow operation, create silent alert for HQ
        alert_msg = (
            f"⚠️ تنبيه رقابي: عملية ({activity_name}) تجاوزت الميزانية "
            f"بنسبة {variance_percentage}%. "
            f"المخطط: {planned_cost}، الفعلي: {actual_cost}، "
            f"مبلغ التجاوز: {variance_amount}."
        )

        VarianceAlert.objects.create(
            farm=farm,
            daily_log=daily_log,
            category=category,
            activity_name=activity_name,
            planned_cost=planned_cost,
            actual_cost=actual_cost,
            variance_amount=variance_amount,
            variance_percentage=variance_percentage,
            alert_message=alert_msg,
            status=VarianceAlert.ALERT_STATUS_UNINVESTIGATED,
        )

        logger.warning("Shadow Alert Triggered: %s", alert_msg)
        return "SHADOW_ALERT_CREATED"

    @staticmethod
    def audit_diesel_consumption(
        farm,
        daily_log,
        asset_name: str,
        actual_liters: Decimal,
        expected_liters: Decimal,
        machine_hours: Decimal,
    ) -> str:
        """
        Specialized audit for diesel dipstick readings.

        Compares actual diesel consumption (from dipstick) against the
        expected consumption (MachineRate.fuel_consumption_rate * hours).

        Uses SystemSettings.diesel_tolerance_percentage as threshold.
        """
        settings = SystemSettings.get_settings()

        if expected_liters <= Decimal('0.0000'):
            return "SKIPPED_NO_PLAN"

        excess = (actual_liters - expected_liters).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )

        if excess <= Decimal('0.0000'):
            return "AUDIT_PASSED_OK"

        deviation_pct = (
            (excess / expected_liters) * Decimal('100.00') # agri-guardian: decimal-safe
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        if deviation_pct <= settings.diesel_tolerance_percentage:
            return "AUDIT_PASSED_OK"

        # --- Diesel anomaly detected ---
        activity_name = f"تشغيل معدة: {asset_name}"

        if ShadowVarianceEngine._is_strict_mode(farm):
            raise ValidationError(
                f"🔴 [ERP BLOCK] شبهة تلاعب بالديزل — {activity_name}. "
                f"الاستهلاك الفعلي ({actual_liters} لتر) يتجاوز المتوقع "
                f"({expected_liters} لتر) لـ {machine_hours} ساعات عمل "
                f"بنسبة {deviation_pct}%. تم إيقاف الاعتماد."
            )

        alert_msg = (
            f"⚠️ شبهة تلاعب بالديزل: {activity_name}. "
            f"الاستهلاك الفعلي ({actual_liters} لتر) يتجاوز الطبيعي "
            f"({expected_liters} لتر) لـ {machine_hours} ساعات عمل "
            f"بنسبة {deviation_pct}%."
        )

        VarianceAlert.objects.create(
            farm=farm,
            daily_log=daily_log,
            category=VarianceAlert.CATEGORY_DIESEL_ANOMALY,
            activity_name=activity_name,
            planned_cost=expected_liters,  # Re-purpose for liters comparison
            actual_cost=actual_liters,
            variance_amount=excess,
            variance_percentage=deviation_pct,
            alert_message=alert_msg,
            status=VarianceAlert.ALERT_STATUS_UNINVESTIGATED,
        )

        logger.warning("Shadow Diesel Alert: %s", alert_msg)
        return "SHADOW_ALERT_CREATED"

    @staticmethod
    def audit_budget_burn_rate(
        farm,
        crop_plan,
        *,
        current_spend: Decimal,
        total_budget: Decimal,
        elapsed_pct: Decimal = Decimal('50.00'),
    ) -> str:
        """
        [AGRI-GUARDIAN §Axis-8] Proactive Budget Burn Rate Monitor.

        Detects when actual spend% significantly outpaces elapsed time%.
        Example: If 80% of budget is burned but only 40% of time has passed,
        the burn rate ratio = 80/40 = 2.0 which exceeds threshold.

        Args:
            current_spend: Total actual spend so far.
            total_budget: Total planned budget.
            elapsed_pct: Percentage of planned time elapsed (0-100).
        """
        if total_budget <= Decimal('0.0000') or elapsed_pct <= Decimal('0.00'):
            return "SKIPPED_NO_PLAN"

        spend_pct = (
            (current_spend / total_budget) * Decimal('100.00')  # agri-guardian: decimal-safe
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Burn rate ratio: spending pace vs time pace
        burn_ratio = (spend_pct / elapsed_pct).quantize(  # agri-guardian: decimal-safe
            Decimal('0.01'), rounding=ROUND_HALF_UP
        ) if elapsed_pct > Decimal('0') else Decimal('0')

        # Threshold: burn ratio > 1.5 triggers alert (spending 50% faster than time)
        BURN_THRESHOLD = Decimal('1.50')

        if burn_ratio <= BURN_THRESHOLD:
            return "AUDIT_PASSED_OK"

        settings = SystemSettings.get_settings()
        plan_name = getattr(crop_plan, 'name', str(crop_plan))

        if ShadowVarianceEngine._is_strict_mode(farm) and spend_pct >= Decimal('90.00'):
            raise ValidationError(
                f"🔴 [ERP BLOCK] معدل حرق الميزانية مرتفع جداً لخطة ({plan_name}). "
                f"تم إنفاق {spend_pct}% بانقضاء {elapsed_pct}% فقط من الوقت. "
                f"نسبة الحرق: {burn_ratio}x. يجب مراجعة إدارة القطاع."
            )

        alert_msg = (
            f"⚠️ تنبيه حرق ميزانية: خطة ({plan_name}) — "
            f"تم إنفاق {spend_pct}% ({current_spend}) من إجمالي {total_budget} "
            f"بانقضاء {elapsed_pct}% من الوقت. "
            f"معدل الحرق: {burn_ratio}x"
        )

        VarianceAlert.objects.create(
            farm=farm,
            category=VarianceAlert.CATEGORY_BUDGET_OVERRUN,
            activity_name=f"حرق ميزانية: {plan_name}",
            planned_cost=total_budget,
            actual_cost=current_spend,
            variance_amount=(current_spend - (total_budget * elapsed_pct / Decimal('100'))).quantize(  # agri-guardian: decimal-safe
                Decimal('0.0001'), rounding=ROUND_HALF_UP
            ),
            variance_percentage=spend_pct,
            alert_message=alert_msg,
            status=VarianceAlert.ALERT_STATUS_UNINVESTIGATED,
        )

        logger.warning("Burn Rate Alert: %s", alert_msg)
        return "SHADOW_ALERT_CREATED"
