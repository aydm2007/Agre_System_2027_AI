from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from django.core.exceptions import ValidationError

from smart_agri.core.services.costing.policy import CostPolicy


def normalize_surrah_share(surrah_value) -> Decimal:
    """Canonical labor unit = Surra (quarter-day increments)."""
    if surrah_value in (None, ""):
        return Decimal("0.00")
    value = Decimal(str(surrah_value))
    if value <= 0:
        return Decimal("0.00")
    return (value * Decimal("4")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal("0.25")


def sync_activity_employees(activity: Any, employees_payload: List[Dict[str, Any]]) -> None:
    """
    Syncs API payload to ActivityEmployee and Timesheet.
    payload example:
      - Registered: {'employee_id': 1, 'surrah_share': 1.0}
      - Casual batch: {'labor_type': 'CASUAL_BATCH', 'workers_count': 12, 'surrah_share': 1.0}
    """
    from smart_agri.core.models.activity import ActivityEmployee
    from smart_agri.core.models.hr import Timesheet, Employee, EmploymentCategory

    ActivityEmployee.objects.filter(activity=activity).delete()
    Timesheet.objects.filter(activity=activity).delete()

    for entry in employees_payload:
        labor_type = str(entry.get("labor_type") or ActivityEmployee.LABOR_REGISTERED).upper()
        surrah_share = normalize_surrah_share(
            entry.get("surrah_share") if entry.get("surrah_share") is not None else entry.get("surra_units"),
        )
        if surrah_share <= 0:
            # We allow 0 if it's hourly mode, but traditionally it was blocked.
            # However, for backward compatibility, if surrah is 0 and is_hourly is False, skip.
            if not entry.get("is_hourly"):
                continue

        # [Omega-2028] Extraction of hourly mode and achievement metrics
        is_hourly = bool(entry.get("is_hourly", False))
        hours_worked = CostPolicy.to_decimal(entry.get("hours_worked") or "0", "hours_worked")
        hourly_rate = CostPolicy.to_decimal(entry.get("hourly_rate") or "0", "hourly_rate")
        achievement_qty = CostPolicy.to_decimal(entry.get("achievement_qty") or "0", "achievement_qty")
        achievement_uom = str(entry.get("achievement_uom") or "").strip()
        fixed_wage_cost = CostPolicy.to_decimal(entry.get("fixed_wage_cost") or "0", "fixed_wage_cost")

        if labor_type == ActivityEmployee.LABOR_CASUAL_BATCH:
            workers_count = CostPolicy.to_decimal(entry.get("workers_count") or "0", "workers_count")
            if workers_count <= 0:
                raise ValidationError("workers_count must be greater than zero for casual labor batch.")

            farm_labor_rate = CostPolicy.get_labor_daily_rate(activity.log.farm_id)
            
            # [Omega-2028] Calculation priority and Intelligent Validation
            standard_cost = (surrah_share * workers_count * farm_labor_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            if fixed_wage_cost > 0:
                # [Forensic Audit] Validate Logical Boundaries (Guardrail Axis 1)
                # Ensure the manual cost isn't completely illogical (e.g. >10x the standard rate)
                if standard_cost > 0:
                    variance_ratio = (
                        fixed_wage_cost / standard_cost  # agri-guardian: decimal-safe
                    ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                    if variance_ratio > Decimal("10") or variance_ratio < Decimal("0.1"):
                        raise ValidationError(
                            f"خطأ مالي حرج: المبلغ المدخل ({fixed_wage_cost}) غير منطقي مقارنة "
                            f"بالسعة والعدد (التكلفة المعيارية: {standard_cost}). يرجى التحقق من الرقم."
                        )
                
                wage_cost = fixed_wage_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total_surrah = surrah_share * workers_count # Keep as metadata for activity tracking
            elif is_hourly:
                wage_cost = (workers_count * hours_worked * hourly_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total_surrah = Decimal("0.00") # Surrah is zeroed in strict hourly mode
            else:
                total_surrah = (surrah_share * workers_count).quantize(Decimal("0.25"), rounding=ROUND_HALF_UP)
                wage_cost = (total_surrah * farm_labor_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            ActivityEmployee.objects.create(
                activity=activity,
                employee=None,
                labor_type=ActivityEmployee.LABOR_CASUAL_BATCH,
                labor_batch_label=(entry.get("labor_batch_label") or "Casual Labor Batch").strip(),
                workers_count=workers_count,
                surrah_share=total_surrah,
                is_hourly=is_hourly,
                hours_worked=hours_worked,
                hourly_rate=hourly_rate,
                achievement_qty=achievement_qty,
                achievement_uom=achievement_uom,
                fixed_wage_cost=fixed_wage_cost if fixed_wage_cost > 0 else None,
                wage_cost=wage_cost,
            )
            continue

        emp_id = entry.get("employee_id")
        employee = Employee.objects.select_related("farm").filter(pk=emp_id).first()
        if not employee:
            raise ValidationError(f"Employee {emp_id} does not exist.")
        if employee.farm_id != activity.log.farm_id:
            raise ValidationError(f"Employee farm scope mismatch for {employee.first_name}.")
        
        if employee.category == EmploymentCategory.OFFICIAL:
            row_wage_cost = Decimal("0.0000")
            if fixed_wage_cost > 0:
                row_wage_cost = fixed_wage_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            elif is_hourly:
                # Registered employees can have hourly costing for internal tracking
                row_wage_cost = (hours_worked * hourly_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            ActivityEmployee.objects.create(
                activity=activity,
                employee_id=emp_id,
                labor_type=ActivityEmployee.LABOR_REGISTERED,
                workers_count=Decimal("0.00"),
                surrah_share=surrah_share if not is_hourly else Decimal("0.00"),
                is_hourly=is_hourly,
                hours_worked=hours_worked,
                hourly_rate=hourly_rate,
                achievement_qty=achievement_qty,
                achievement_uom=achievement_uom,
                fixed_wage_cost=fixed_wage_cost if fixed_wage_cost > 0 else None,
                wage_cost=row_wage_cost,
            )
            Timesheet.objects.create(
                employee_id=emp_id,
                farm=activity.log.farm,
                date=activity.log.log_date,
                activity=activity,
                surrah_count=surrah_share,
                surrah_overtime=Decimal("0.00"),
                is_approved=False,
            )
            continue

        # CASUAL Registered Worker
        # [Omega-2028] Intelligent Validation for Registered Workers
        standard_cost = (surrah_share * (employee.shift_rate or Decimal("0.0000"))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        if fixed_wage_cost > 0:
            if standard_cost > 0:
                variance_ratio = (
                    fixed_wage_cost / standard_cost  # agri-guardian: decimal-safe
                ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                if variance_ratio > Decimal("10") or variance_ratio < Decimal("0.1"):
                    raise ValidationError(
                        f"خطأ مالي حرج: المبلغ المدخل ({fixed_wage_cost}) غير منطقي للموظف "
                        f"{employee.first_name} (المعياري: {standard_cost})."
                    )

            wage_cost = fixed_wage_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            row_surrah = surrah_share
        elif is_hourly:
            wage_cost = (hours_worked * hourly_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            row_surrah = Decimal("0.00")
        else:
            wage_cost = (surrah_share * (employee.shift_rate or Decimal("0.0000"))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            row_surrah = surrah_share

        ActivityEmployee.objects.create(
            activity=activity,
            employee_id=emp_id,
            labor_type=ActivityEmployee.LABOR_REGISTERED,
            workers_count=Decimal("0.00"),
            surrah_share=row_surrah,
            is_hourly=is_hourly,
            hours_worked=hours_worked,
            hourly_rate=hourly_rate,
            achievement_qty=achievement_qty,
            achievement_uom=achievement_uom,
            fixed_wage_cost=fixed_wage_cost if fixed_wage_cost > 0 else None,
            wage_cost=wage_cost,
        )
        Timesheet.objects.create(
            employee_id=emp_id,
            farm=activity.log.farm,
            date=activity.log.log_date,
            activity=activity,
            surrah_count=surrah_share,
            surrah_overtime=Decimal("0.00"),
            is_approved=False,
        )
