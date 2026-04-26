from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError


class HarvestComplianceService:
    """Mandatory harvest compliance checks before posting or quarantine release."""

    @staticmethod
    def validate(*, location_id, crop_plan_id, gross_qty, attachments_count: int, require_attachment: bool = True, lot_code: str | None = None) -> dict:
        if not location_id:
            raise ValidationError("موقع الحصاد إلزامي.")
        if not crop_plan_id:
            raise ValidationError("الخطة الزراعية المرتبطة بالحصاد إلزامية.")
        quantity = Decimal(str(gross_qty or 0)).quantize(Decimal("0.0001"))
        if quantity <= 0:
            raise ValidationError("كمية الحصاد يجب أن تكون أكبر من صفر.")
        if require_attachment and attachments_count < 1:
            raise ValidationError("مرفق إثبات الحصاد إلزامي في الوضع المؤسسي.")
        if not lot_code:
            raise ValidationError("رمز التشغيلة/الدفعة إلزامي لتتبع الحصاد.")
        return {
            "status": "compliant",
            "gross_qty": str(quantity),
            "attachments_count": attachments_count,
            "lot_code": lot_code,
            "quarantine_release_ready": attachments_count >= 1 and quantity > 0,
        }
