from django.core.exceptions import ValidationError
from django.utils import timezone

from smart_agri.core.models import Farm
from smart_agri.finance.models_treasury import TreasuryTransaction
from smart_agri.finance.services.core_finance import FinanceService


class TreasuryService:
    """Governed service-layer entry point for append-only treasury mutations."""

    @staticmethod
    def create_transaction(*, user, farm_id, idempotency_key, **validated_data) -> TreasuryTransaction:
        try:
            farm = Farm.objects.get(pk=farm_id)
        except Farm.DoesNotExist as exc:
            raise ValidationError("المزرعة المحددة غير موجودة.") from exc

        cash_box = validated_data.get("cash_box")
        if cash_box and cash_box.farm_id != farm_id:
            raise ValidationError({"cash_box": "الصندوق النقدي يجب أن ينتمي إلى المزرعة النشطة."})

        FinanceService.check_fiscal_period(timezone.localdate(), farm, strict=True)

        transaction_obj = TreasuryTransaction(
            farm=farm,
            idempotency_key=idempotency_key,
            created_by=user,
            **validated_data,
        )
        transaction_obj.full_clean()
        transaction_obj.save()

        return transaction_obj
