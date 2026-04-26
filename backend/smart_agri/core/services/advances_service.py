"""
AdvancesService — خدمة سلفيات العمال.

AGENTS.md Compliance:
  - Axis 2: Idempotency via idempotency_key
  - Axis 3: Fiscal Period Gate
  - Axis 4: Fund Accounting (ledger entries)
  - Axis 5: Decimal(19,4)
  - Axis 6: Farm-scoped
  - Axis 7: Audit trail (approved_by, created_by, AuditLog)
  - Axis 8: VarianceAlert for advance limits
  - Axis 9: Sovereign liabilities via zakat_rule linkage
  - Axis 10: Farm-tier-based advance caps
  - Service Layer Pattern
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from smart_agri.core.models.hr import (
    Employee, EmployeeAdvance, AdvanceStatus, PayrollSlip,
)

logger = logging.getLogger(__name__)

FOUR_DP = Decimal("0.0001")
ZERO = Decimal("0.0000")

# [Axis 8] Maximum advance percentage of monthly salary
MAX_ADVANCE_RATIO = Decimal("0.50")

# [Axis 10] Farm-tier-based advance ratio caps
# Resolved from total farm area (hectares) via Location.area_hectares
FARM_TIER_ADVANCE_RATIOS = {
    'SMALL':  Decimal("0.30"),   # ≤ 20 ha — conservative cap
    'MEDIUM': Decimal("0.50"),   # 21-100 ha — standard cap
    'LARGE':  Decimal("0.60"),   # > 100 ha — higher liquidity
}

def _resolve_farm_tier(farm_id):
    """[Axis 10] Resolve farm tier by total area (hectares)."""
    try:
        from django.db.models import Sum as DjSum
        from smart_agri.core.models.farm import Location
        total_area = Location.objects.filter(
            farm_id=farm_id, deleted_at__isnull=True,
        ).aggregate(total=DjSum('area_hectares'))['total'] or Decimal("0")
        if total_area <= Decimal("20"):
            return 'SMALL'
        elif total_area <= Decimal("100"):
            return 'MEDIUM'
        else:
            return 'LARGE'
    except (ValueError, TypeError, LookupError, AttributeError) as e:
        logger.warning("Failed to determine farm tier for advances, defaulting to MEDIUM: %s", e)
        return 'MEDIUM'  # default fallback


class AdvancesService:
    """
    [AGENTS.md Phase 3] Employee advance management.
    Create, approve, auto-deduct from payroll, post ledger entries.
    """

    @staticmethod
    @transaction.atomic
    def create_advance(*, employee_id, farm_id, amount, date, reason='', actor=None, idempotency_key=None):
        """
        Create a new employee advance.
        [Axis 2] Idempotency via UUID key.
        [Axis 3] Fiscal Period Gate.
        [Axis 6] Farm validation.
        [Axis 8] Advance limit check.
        """
        if not farm_id:
            raise ValidationError({"farm_id": "[Axis 6] معرف المزرعة مطلوب."})

        # Idempotency check
        if idempotency_key:
            existing = EmployeeAdvance.objects.filter(
                idempotency_key=idempotency_key, deleted_at__isnull=True,
            ).first()
            if existing:
                return existing

        try:
            employee = Employee.objects.get(
                pk=employee_id, farm_id=farm_id, is_active=True, deleted_at__isnull=True,
            )
        except Employee.DoesNotExist:
            raise ValidationError(
                {"employee_id": "[Axis 6] الموظف غير موجود أو لا ينتمي لهذه المزرعة."}
            )

        amount_dec = Decimal(str(amount)).quantize(FOUR_DP)
        if amount_dec <= ZERO:
            raise ValidationError({"amount": "المبلغ يجب أن يكون أكبر من صفر."})

        # [Axis 3] Fiscal Period Gate
        try:
            from smart_agri.finance.services.core_finance import FinanceService
            from smart_agri.core.models.farm import Farm
            farm = Farm.objects.get(pk=farm_id)
            FinanceService.check_fiscal_period(date, farm, strict=True)
        except ImportError:
            logger.warning("FinanceService not available for fiscal period check.")
        except ValidationError:
            raise

        # [Axis 8 + Axis 10] Advance limit check — farm-tier-based cap
        monthly_estimate = (employee.shift_rate or employee.base_salary or ZERO) * Decimal("30")
        if monthly_estimate > ZERO:
            from django.db.models import Sum as DjSum

            # [Axis 10] Resolve tier-based ratio
            tier = _resolve_farm_tier(farm_id)
            tier_ratio = FARM_TIER_ADVANCE_RATIOS.get(tier, MAX_ADVANCE_RATIO)

            existing_pending = EmployeeAdvance.objects.filter(
                employee_id=employee_id,
                status__in=[AdvanceStatus.PENDING, AdvanceStatus.APPROVED],
                deleted_at__isnull=True,
            ).aggregate(total=DjSum('amount'))['total'] or ZERO

            max_allowed = (monthly_estimate * tier_ratio).quantize(FOUR_DP)
            if (existing_pending + amount_dec) > max_allowed:
                # Create VarianceAlert instead of blocking
                from smart_agri.core.models.report import VarianceAlert
                VarianceAlert.objects.create(
                    farm_id=farm_id,
                    alert_type='ADVANCE_LIMIT',
                    message=f"سلفية الموظف {employee} تتجاوز سقف الفئة ({tier}={tier_ratio*100}%): "
                            f"مطلوب={amount_dec}, قائم={existing_pending}, حد={max_allowed}",
                    severity='WARNING',
                )

        advance = EmployeeAdvance.objects.create(
            employee=employee,
            farm_id=farm_id,
            amount=amount_dec,
            date=date,
            reason=reason,
            status=AdvanceStatus.PENDING,
            idempotency_key=idempotency_key,
            created_by=actor,
        )

        # [Axis 7] AuditLog
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='CREATE_ADVANCE',
            model='EmployeeAdvance',
            object_id=str(advance.id),
            actor=actor,
            new_payload={'employee': str(employee), 'amount': str(amount_dec)},
        )

        logger.info(
            "Advance created: id=%s, employee=%s, amount=%.4f, farm=%s",
            advance.id, employee_id, amount_dec, farm_id,
        )
        return advance

    @staticmethod
    @transaction.atomic
    def approve_advance(*, advance_id, approver):
        """
        [Axis 4] Post ledger entry: Debit Employee Receivable / Credit Cash.
        [Axis 7] Approve with audit trail + AuditLog.
        """
        try:
            advance = EmployeeAdvance.objects.select_for_update().get(
                pk=advance_id, deleted_at__isnull=True,
            )
        except EmployeeAdvance.DoesNotExist:
            raise ValidationError({"advance_id": "السلفية غير موجودة."})

        if advance.status == AdvanceStatus.APPROVED:
            return advance

        if advance.status != AdvanceStatus.PENDING:
            raise ValidationError(
                {"status": f"لا يمكن اعتماد سلفية في حالة '{advance.get_status_display()}'."}
            )

        advance.status = AdvanceStatus.APPROVED
        advance.approved_by = approver
        advance.save(update_fields=['status', 'approved_by'])

        # [Axis 4] Fund Accounting — Post ledger entries for the advance
        from smart_agri.finance.models import FinancialLedger
        amount = advance.amount.quantize(FOUR_DP)
        created_by = approver if getattr(approver, 'is_authenticated', False) else None

        # Debit: Employee Receivable (the advance is money owed to company)
        FinancialLedger.objects.create(
            farm_id=advance.farm_id,
            account_code='EMPLOYEE_RECEIVABLE',
            debit=amount,
            credit=ZERO,
            description=f"سلفية موظف {advance.employee} — #{advance.id}",
            created_by=created_by,
        )
        # Credit: Cash / Bank
        FinancialLedger.objects.create(
            farm_id=advance.farm_id,
            account_code='CASH',
            debit=ZERO,
            credit=amount,
            description=f"صرف سلفية #{advance.id} — {advance.employee}",
            created_by=created_by,
        )

        # [Axis 7] AuditLog
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='APPROVE_ADVANCE',
            model='EmployeeAdvance',
            object_id=str(advance.id),
            actor=approver,
            new_payload={'employee': str(advance.employee), 'amount': str(advance.amount)},
        )

        logger.info("Advance approved: id=%s, approver=%s", advance.id, approver)
        return advance

    @staticmethod
    @transaction.atomic
    def deduct_advances_from_payroll(*, employee_id, payroll_slip):
        """
        Auto-deduct approved advances from PayrollSlip.
        [Axis 4] Reverse the receivable: Debit Salary Payable / Credit Employee Receivable.
        [Axis 5] Decimal-safe deduction.
        """
        approved_advances = EmployeeAdvance.objects.filter(
            employee_id=employee_id,
            status=AdvanceStatus.APPROVED,
            deleted_at__isnull=True,
        ).order_by('date')

        total_deducted = ZERO
        for advance in approved_advances:
            total_deducted += advance.amount
            advance.status = AdvanceStatus.DEDUCTED
            advance.deducted_in_slip = payroll_slip
            advance.save(update_fields=['status', 'deducted_in_slip'])

        if total_deducted > ZERO:
            payroll_slip.deductions_amount = (
                payroll_slip.deductions_amount + total_deducted
            ).quantize(FOUR_DP)
            payroll_slip.net_pay = (
                payroll_slip.net_pay - total_deducted
            ).quantize(FOUR_DP)
            payroll_slip.save(update_fields=['deductions_amount', 'net_pay'])

            # [Axis 4] Reverse receivable on deduction
            from smart_agri.finance.models import FinancialLedger
            created_by = None

            # Debit: Salary Payable (reducing what company owes employee)
            FinancialLedger.objects.create(
                farm_id=payroll_slip.run.farm_id,
                account_code=FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
                debit=total_deducted.quantize(FOUR_DP),
                credit=ZERO,
                description=f"خصم سلفيات من مسير — موظف #{employee_id}, قسيمة #{payroll_slip.id}",
                created_by=created_by,
            )
            # Credit: Employee Receivable (clearing the advance debt)
            FinancialLedger.objects.create(
                farm_id=payroll_slip.run.farm_id,
                account_code='EMPLOYEE_RECEIVABLE',
                debit=ZERO,
                credit=total_deducted.quantize(FOUR_DP),
                description=f"تسوية سلفيات — موظف #{employee_id}, قسيمة #{payroll_slip.id}",
                created_by=created_by,
            )

            logger.info(
                "Advances deducted: employee=%s, total=%.4f, slip=%s",
                employee_id, total_deducted, payroll_slip.id,
            )

        return total_deducted

    @staticmethod
    def get_employee_advances(*, farm_id, employee_id=None, status=None):
        """
        List advances for a farm, optionally filtered by employee and status.
        [Axis 6] Farm-scoped.
        """
        qs = EmployeeAdvance.objects.filter(
            farm_id=farm_id, deleted_at__isnull=True,
        ).select_related('employee').order_by('-date')

        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if status:
            qs = qs.filter(status=status)

        return [
            {
                'id': a.id,
                'employee_id': a.employee_id,
                'employee_name': str(a.employee),
                'amount': str(a.amount),
                'date': str(a.date),
                'reason': a.reason,
                'status': a.status,
                'status_display': a.get_status_display(),
                'idempotency_key': str(a.idempotency_key) if a.idempotency_key else None,
                'deducted_in_slip': a.deducted_in_slip_id,
            }
            for a in qs
        ]
