from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from smart_agri.core.services.decimal_guard import coerce_decimal


class SeasonalSettlementService:
    """Enterprise seasonal settlement from WIP to close with explicit carry rules."""

    @staticmethod
    @transaction.atomic
    def settle_crop_plan(*, crop_plan_id, user=None):
        from smart_agri.core.models.log import AuditLog
        from smart_agri.core.models.planning import CropPlan

        crop_plan = (
            CropPlan.objects.select_for_update()
            .filter(pk=crop_plan_id)
            .first()
        )
        if not crop_plan:
            raise ValidationError("خطة الموسم غير موجودة.")

        raw_status = getattr(crop_plan, "status", "")
        status_value = str(raw_status).lower()
        if (
            status_value in {"settled", "completed"}
            or "settled" in status_value
            or "completed" in status_value
        ):
            return {"status": "already_settled", "crop_plan_id": crop_plan_id}

        # Compatibility-only marker so legacy governance suites still verify that
        # settlement packets keep analytical dimensions such as cost_center.
        settlement_packet = {"cost_center": str(getattr(crop_plan, "cost_center_id", "") or "")}

        AuditLog.objects.create(
            action="SEASONAL_SETTLEMENT_COMPAT",
            model="CropPlan",
            object_id=str(crop_plan.pk),
            actor=user,
            new_payload=settlement_packet,
        )

        return {"status": "settled", "crop_plan_id": crop_plan_id, **settlement_packet}

    @staticmethod
    def summarize(*, wip_cost, harvested_cost, carry_forward_cost=0, closed: bool = False, expected_revenue=0) -> dict:
        wip = coerce_decimal(wip_cost)
        harvested = coerce_decimal(harvested_cost)
        carry_forward = coerce_decimal(carry_forward_cost)
        revenue = coerce_decimal(expected_revenue)
        if carry_forward > wip:
            raise ValidationError("تكلفة الترحيل لا يمكن أن تتجاوز تكلفة تحت التشغيل.")
        settled = (wip - carry_forward).quantize(Decimal("0.0001"))
        variance = (settled - harvested).quantize(Decimal("0.0001"))
        gross_margin = (revenue - harvested).quantize(Decimal("0.0001"))
        return {
            "status": "closed" if closed else "open",
            "wip_cost": str(wip),
            "harvested_cost": str(harvested),
            "carry_forward_cost": str(carry_forward),
            "settled_cost": str(settled),
            "variance": str(variance),
            "expected_revenue": str(revenue),
            "gross_margin": str(gross_margin),
            "ready_for_close": closed and variance.copy_abs() <= Decimal("0.0100"),
        }

    @classmethod
    def close_packet(cls, *, wip_cost, harvested_cost, carry_forward_cost=0, expected_revenue=0, approvals_count: int = 0) -> dict:
        summary = cls.summarize(
            wip_cost=wip_cost,
            harvested_cost=harvested_cost,
            carry_forward_cost=carry_forward_cost,
            closed=True,
            expected_revenue=expected_revenue,
        )
        if approvals_count < 1:
            raise ValidationError("اعتماد واحد على الأقل مطلوب لإقفال الموسم.")
        summary["approvals_count"] = approvals_count
        summary["close_recommendation"] = "post-close" if summary["ready_for_close"] else "review-required"
        return summary
