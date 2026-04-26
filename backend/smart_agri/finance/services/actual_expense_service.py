from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from smart_agri.core.api.permissions import (
    _ensure_user_has_farm_access,
    user_has_any_farm_role,
    user_has_farm_role,
)
from smart_agri.finance.models import ActualExpense, SectorRelationship
from smart_agri.finance.services.core_finance import FinanceService


class ActualExpenseService:
    """Governed service-layer mutations for mutable actual expenses."""

    @staticmethod
    def ensure_finance_operator(user, farm_id=None):
        if getattr(user, "is_superuser", False):
            return
        if user.has_perm("finance.can_manage_expenses"):
            return
        if farm_id and user_has_farm_role(user, farm_id, {"Admin", "Manager"}):
            return
        if not farm_id and user_has_any_farm_role(user, {"Admin", "Manager"}):
            return
        raise PermissionDenied("هذه العملية المالية تتطلب صلاحية مالية معتمدة.")

    @staticmethod
    def calculate_amount_local(amount, exchange_rate):
        if amount is None or exchange_rate is None:
            return Decimal("0.0000")
        return (amount * exchange_rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    @staticmethod
    @transaction.atomic
    def create_expense(*, user, **validated_data) -> ActualExpense:
        farm = validated_data.get("farm")
        ActualExpenseService.ensure_finance_operator(user, farm.id if farm else None)
        if farm and not getattr(user, "is_superuser", False):
            _ensure_user_has_farm_access(user, farm.id)
        relationship = SectorRelationship.objects.filter(farm=farm).first()
        if not relationship:
            raise ValidationError({"farm": "يجب تعريف علاقة القطاع قبل ترحيل المصروفات."})
        FinanceService.check_fiscal_period(validated_data.get("date"), farm, strict=True)
        instance = ActualExpense(**validated_data)
        instance.amount_local = ActualExpenseService.calculate_amount_local(instance.amount, instance.exchange_rate)
        instance.full_clean()
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def update_expense(*, user, instance: ActualExpense, **validated_data) -> ActualExpense:
        locked_instance = ActualExpense.objects.select_for_update().get(pk=instance.pk)
        farm = validated_data.get("farm") or locked_instance.farm
        ActualExpenseService.ensure_finance_operator(user, farm.id if farm else None)
        if farm and not getattr(user, "is_superuser", False):
            _ensure_user_has_farm_access(user, farm.id)
        relationship = SectorRelationship.objects.filter(farm=farm).first()
        if not relationship:
            raise ValidationError({"farm": "يجب تعريف علاقة القطاع قبل تعديل المصروفات."})
        updated_date = validated_data.get("date", locked_instance.date)
        FinanceService.check_fiscal_period(updated_date, farm, strict=True)
        for field, value in validated_data.items():
            setattr(locked_instance, field, value)
        locked_instance.amount_local = ActualExpenseService.calculate_amount_local(
            locked_instance.amount,
            locked_instance.exchange_rate,
        )
        locked_instance.full_clean()
        locked_instance.save()
        return locked_instance


    @staticmethod
    @transaction.atomic
    def delete_expense(*, user, instance: ActualExpense) -> None:
        locked_instance = ActualExpense.objects.select_for_update().get(pk=instance.pk)
        ActualExpenseService.ensure_finance_operator(user, locked_instance.farm_id)
        if locked_instance.farm_id and not getattr(user, "is_superuser", False):
            _ensure_user_has_farm_access(user, locked_instance.farm_id)
        FinanceService.check_fiscal_period(locked_instance.date, locked_instance.farm, strict=True)
        locked_instance.delete()

    @staticmethod
    @transaction.atomic
    def allocate_expense(*, user, expense_id: int) -> ActualExpense:
        expense = ActualExpense.objects.select_for_update().select_related("farm").get(pk=expense_id)
        ActualExpenseService.ensure_finance_operator(user, expense.farm_id)
        if expense.is_allocated:
            raise ValidationError("المصروف مخصص بالفعل")
        FinanceService.check_fiscal_period(expense.date, expense.farm, strict=True)
        expense.is_allocated = True
        expense.allocated_at = timezone.now()
        expense.save(update_fields=["is_allocated", "allocated_at"])
        return expense
