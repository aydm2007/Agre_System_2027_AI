from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from django.core.exceptions import ValidationError, ObjectDoesNotExist

from smart_agri.core.models.hr import Employee
from smart_agri.core.services.costing.policy import CostPolicy


FOUR_DP = Decimal("0.0001")


def _to_decimal(value, field_name: str) -> Decimal:
    if value in (None, ""):
        raise ValidationError({field_name: "هذا الحقل مطلوب."})
    if isinstance(value, float):
        raise ValidationError({field_name: "القيم المالية يجب أن تكون Decimal وليست float."})
    try:
        return Decimal(str(value))
    except (ValidationError, ValueError, ObjectDoesNotExist) as exc:
        raise ValidationError({field_name: "قيمة رقمية غير صالحة."}) from exc


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(FOUR_DP, rounding=ROUND_HALF_UP)


class LaborEstimationService:
    """Read-only estimator for daily labor preview in Daily Log."""

    DEFAULT_PERIOD_HOURS = Decimal("8.0000")
    DEFAULT_CURRENCY = "YER"

    @classmethod
    def preview_for_casual(
        cls,
        *,
        farm_id: int,
        surrah_count,
        workers_count,
        period_hours=None,
    ) -> dict:
        surrah = _to_decimal(surrah_count, "surrah_count")
        if surrah <= 0:
            raise ValidationError({"surrah_count": "يجب أن يكون أكبر من صفر."})

        try:
            workers = int(workers_count)
        except (ValidationError, ValueError, ObjectDoesNotExist) as exc:
            raise ValidationError({"workers_count": "قيمة عدد العمالة غير صالحة."}) from exc
        if workers <= 0:
            raise ValidationError({"workers_count": "يجب أن يكون أكبر من صفر."})

        period = _to_decimal(period_hours, "period_hours") if period_hours is not None else cls.DEFAULT_PERIOD_HOURS
        if period <= 0:
            raise ValidationError({"period_hours": "يجب أن يكون أكبر من صفر."})

        farm_labor_rate = CostPolicy.get_labor_daily_rate(farm_id)
        equivalent_hours_per_worker = _quantize(surrah * period)
        equivalent_hours_total = _quantize(equivalent_hours_per_worker * Decimal(workers))
        estimated_labor_cost = _quantize(Decimal(workers) * surrah * farm_labor_rate)

        return {
            "period_hours": str(_quantize(period)),
            "surrah_count": str(_quantize(surrah)),
            "equivalent_hours_per_worker": str(equivalent_hours_per_worker),
            "equivalent_hours_total": str(equivalent_hours_total),
            "estimated_labor_cost": str(estimated_labor_cost),
            "currency": cls.DEFAULT_CURRENCY,
            "rate_basis": "farm_labor_rate",
        }

    @classmethod
    def preview_for_registered(
        cls,
        *,
        farm_id: int,
        surrah_count,
        employee_ids: Iterable[int],
        period_hours=None,
    ) -> dict:
        surrah = _to_decimal(surrah_count, "surrah_count")
        if surrah <= 0:
            raise ValidationError({"surrah_count": "يجب أن يكون أكبر من صفر."})

        if not employee_ids:
            raise ValidationError({"employee_ids": "قائمة الموظفين مطلوبة."})

        employee_ids_int = []
        for raw in employee_ids:
            try:
                employee_ids_int.append(int(raw))
            except (ValidationError, ValueError, ObjectDoesNotExist) as exc:
                raise ValidationError({"employee_ids": "قائمة الموظفين تحتوي قيماً غير صالحة."}) from exc

        period = _to_decimal(period_hours, "period_hours") if period_hours is not None else cls.DEFAULT_PERIOD_HOURS
        if period <= 0:
            raise ValidationError({"period_hours": "يجب أن يكون أكبر من صفر."})

        employees = list(
            Employee.objects.filter(pk__in=employee_ids_int, is_active=True, deleted_at__isnull=True)
            .only("id", "farm_id", "shift_rate")
        )

        if len(employees) != len(set(employee_ids_int)):
            raise ValidationError({"employee_ids": "يوجد موظفون غير موجودين أو غير نشطين."})
        if any(emp.farm_id != farm_id for emp in employees):
            raise ValidationError({"employee_ids": "بعض الموظفين خارج نطاق المزرعة المحددة."})

        equivalent_hours_per_worker = _quantize(surrah * period)
        equivalent_hours_total = _quantize(equivalent_hours_per_worker * Decimal(len(employees)))
        estimated_labor_cost = _quantize(
            sum((surrah * Decimal(emp.shift_rate or Decimal("0.0000")) for emp in employees), Decimal("0.0000"))
        )

        return {
            "period_hours": str(_quantize(period)),
            "surrah_count": str(_quantize(surrah)),
            "equivalent_hours_per_worker": str(equivalent_hours_per_worker),
            "equivalent_hours_total": str(equivalent_hours_total),
            "estimated_labor_cost": str(estimated_labor_cost),
            "currency": cls.DEFAULT_CURRENCY,
            "rate_basis": "employee_shift_rates",
        }
