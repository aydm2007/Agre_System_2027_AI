from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError

from smart_agri.core.services.decimal_guard import coerce_decimal, safe_decimal_divide


class SharecroppingSettlementService:
    """Normalize sharecropping settlement percentages, values, and remainder checks."""

    @staticmethod
    def settle(*, gross_qty, institution_share, partner_share=None, unit_price=0) -> dict:
        gross = coerce_decimal(gross_qty)
        institution = coerce_decimal(institution_share, places=Decimal("0.000001"))
        partner = coerce_decimal(partner_share if partner_share is not None else (Decimal("1") - institution), places=Decimal("0.000001"))
        total_share = (institution + partner).quantize(Decimal("0.000001"))
        if total_share <= Decimal("0"):
            raise ValidationError("إجمالي نسب المشاركة يجب أن يكون أكبر من صفر.")
        if total_share != Decimal("1.000000"):
            normalized_institution = safe_decimal_divide(institution, total_share, places=Decimal("0.000001"))
            institution = normalized_institution
            partner = (Decimal("1") - normalized_institution).quantize(Decimal("0.000001"))
        institution_qty = (gross * institution).quantize(Decimal("0.0001"))
        partner_qty = (gross * partner).quantize(Decimal("0.0001"))
        remainder_qty = (gross - institution_qty - partner_qty).quantize(Decimal("0.0001"))
        price = coerce_decimal(unit_price)
        return {
            "gross_qty": str(gross),
            "institution_qty": str(institution_qty),
            "partner_qty": str(partner_qty),
            "remainder_qty": str(remainder_qty),
            "institution_share": str(institution),
            "partner_share": str(partner),
            "institution_value": str((institution_qty * price).quantize(Decimal("0.0001"))),
            "partner_value": str((partner_qty * price).quantize(Decimal("0.0001"))),
            "settlement_balanced": remainder_qty.copy_abs() <= Decimal("0.0100"),
        }
