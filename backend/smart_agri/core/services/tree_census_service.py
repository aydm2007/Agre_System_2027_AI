from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from smart_agri.core.models.inventory import (
    BiologicalAssetCohort,
    BiologicalAssetTransaction,
    TreeCensusVarianceAlert,
)


class TreeCensusService:
    """Service-layer workflow for TreeCensus variance reconciliation."""

    @staticmethod
    def resolve_variance_alert(
        *,
        alert: TreeCensusVarianceAlert,
        cohort_id,
        actor,
        notes: str = "",
        create_ratoon: bool = False,
    ) -> dict:
        with transaction.atomic():
            cohort = BiologicalAssetCohort.objects.select_for_update().filter(
                pk=cohort_id,
                farm=alert.farm,
                location=alert.location,
                crop=alert.crop,
            ).first()
            if cohort is None:
                raise ValidationError(
                    {
                        "detail": "الدفعة المختارة غير موجودة أو لا تطابق المزرعة/الموقع/المحصول المسجل في التنبيه."
                    }
                )

            if alert.missing_quantity > cohort.quantity:
                raise ValidationError(
                    {
                        "detail": (
                            f"كمية العجز ({alert.missing_quantity}) تتجاوز رصيد الدفعة ({cohort.quantity}). "
                            "تحقق من الدفعة الصحيحة."
                        )
                    }
                )

            original_status = cohort.status
            cohort.quantity -= alert.missing_quantity
            if cohort.quantity == 0:
                cohort.status = BiologicalAssetCohort.STATUS_EXCLUDED
            cohort.save(update_fields=["quantity", "status", "updated_at"])
            new_status = (
                BiologicalAssetCohort.STATUS_EXCLUDED
                if cohort.quantity == 0
                else original_status
            )

            BiologicalAssetTransaction.objects.create(
                cohort=cohort,
                farm=alert.farm,
                from_status=original_status,
                to_status=new_status,
                quantity=alert.missing_quantity,
                notes=f"[Loss Resolution] Alert #{alert.pk}: {alert.reason}. {notes}".strip(),
                reference_id=f"variance-alert-{alert.pk}",
            )

            alert.status = TreeCensusVarianceAlert.STATUS_RESOLVED
            alert.resolved_by = actor
            alert.resolved_at = timezone.now()
            alert.cohort = cohort
            alert.save(update_fields=["status", "resolved_by", "resolved_at", "cohort"])

            ratoon_cohort = None
            if create_ratoon:
                ratoon_cohort = BiologicalAssetCohort.objects.create(
                    farm=cohort.farm,
                    location=cohort.location,
                    crop=cohort.crop,
                    variety=cohort.variety,
                    parent_cohort=cohort,
                    batch_name=f"خلفة {cohort.batch_name} ({date.today().year})",
                    status=BiologicalAssetCohort.STATUS_RENEWING,
                    quantity=alert.missing_quantity,
                    planted_date=date.today(),
                )
                BiologicalAssetTransaction.objects.create(
                    cohort=ratoon_cohort,
                    farm=alert.farm,
                    from_status=None,
                    to_status=BiologicalAssetCohort.STATUS_RENEWING,
                    quantity=alert.missing_quantity,
                    notes=f"[Ratooning] خلفة من الدفعة #{cohort.pk} بعد إعدام {alert.missing_quantity} شجرة.",
                    reference_id=f"ratoon-from-{cohort.pk}",
                )

        return {
            "alert": alert,
            "cohort": cohort,
            "ratoon_cohort": ratoon_cohort,
        }
