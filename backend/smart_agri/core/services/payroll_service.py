from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from smart_agri.core.models import Farm, Employee, EmploymentContract, Timesheet, PayrollRun, PayrollSlip
from smart_agri.core.models.hr import EmploymentCategory, PayrollStatus
from smart_agri.finance.models import FinancialLedger
from smart_agri.core.models.log import AuditLog
import logging

logger = logging.getLogger(__name__)

class PayrollService:
    """
    [AGRI-GUARDIAN] AgriAsset Yemen: 'Surra' Based Payroll.
    No minute-tracking. Discrete daily units only (0.25, 0.50, 0.75, 1.00).
    Protocol XXI: The Daily Rate Standard.
    """
    
    def calculate_worker_due(self, worker, attendance_records):
        """
        Calculate total due based on 'Surra' units.
        """
        total_surra = Decimal('0.00')
        contract = worker.contracts.filter(is_active=True).order_by("-start_date").first()
        if worker.category == EmploymentCategory.OFFICIAL:
            if not contract:
                raise ValidationError(f"Official employee {worker.employee_id} requires active contract.")
            return contract.total_monthly_package().quantize(Decimal("0.01"))
        # Legacy compatibility: when a contract with fixed salary exists and no shift rate is configured,
        # preserve contract-driven payroll output expected by older modules/tests.
        if contract and (worker.shift_rate or Decimal("0.00")) <= 0 and contract.basic_salary > 0:
            return contract.total_monthly_package().quantize(Decimal("0.01"))

        for record in attendance_records:
            day_fraction = self._normalize_to_quarter(getattr(record, "surrah_count", Decimal("0.00")))
            overtime_fraction = self._normalize_to_quarter(getattr(record, "surrah_overtime", Decimal("0.00")))
            total_surra += (day_fraction * (worker.shift_rate or Decimal("0.0000")))

            overtime_shift_value = contract.overtime_shift_value if contract else Decimal("0.00")
            total_surra += (overtime_fraction * overtime_shift_value)

        return total_surra.quantize(Decimal("0.01"))

    def _normalize_to_quarter(self, value):
        """Snaps work duration to nearest quarter day (E.g. 0.25, 0.50, 0.75, 1.00)"""
        if not value:
            return Decimal('0.00')
        # Logic to round to nearest 0.25
        # Example: 0.13 -> 0.25, 0.4 -> 0.5, 0.9 -> 1.0
        # Actually standard rounding: round(value * 4) / 4
        try:
            val_dec = Decimal(str(value))
            return (val_dec * 4).quantize(Decimal("1."), rounding='ROUND_HALF_UP') * Decimal("0.25")
        except (ValueError, TypeError, ArithmeticError) as exc:
            logger.warning("Failed to normalize surra value '%s': %s", value, exc)
            return Decimal('0.00')

    @staticmethod
    @transaction.atomic
    def generate_payroll_run(farm: Farm, start_date, end_date, user):
        """
        Generates a DRAFT Payroll Run using Sura Logic.
        """
        employees = Employee.objects.filter(
            deleted_at__isnull=True,
            farm=farm,
            is_active=True,
        ).select_related("farm")

        run = PayrollRun.objects.create(
            farm=farm,
            period_start=start_date,
            period_end=end_date,
            status=PayrollStatus.DRAFT,
            total_amount=Decimal("0.00"),
        )

        service = PayrollService()
        total_amount = Decimal("0.00")

        for employee in employees:
            timesheets = Timesheet.objects.filter(
                deleted_at__isnull=True,
                employee=employee,
                date__gte=start_date,
                date__lte=end_date,
            )
            contract = employee.contracts.filter(is_active=True).order_by("-start_date").first()

            overtime_amount = Decimal("0.00")
            allowances_amount = Decimal("0.00")
            basic_amount = service.calculate_worker_due(employee, timesheets)
            if contract and (employee.shift_rate or Decimal("0.00")) <= 0 and contract.basic_salary > 0:
                basic_amount = Decimal(contract.basic_salary or 0).quantize(Decimal("0.01"))
                allowances_amount = (
                    Decimal(contract.housing_allowance or 0)
                    + Decimal(contract.transport_allowance or 0)
                    + Decimal(contract.other_allowance or 0)
                ).quantize(Decimal("0.01"))
            deductions_amount = Decimal("0.00")
            net_pay = (basic_amount + allowances_amount + overtime_amount - deductions_amount).quantize(
                Decimal("0.01")
            )

            days_worked = Decimal("0.0")
            if employee.category != EmploymentCategory.OFFICIAL:
                for ts in timesheets:
                    days_worked += service._normalize_to_quarter(ts.surrah_count)

            slip = PayrollSlip.objects.create(
                run=run,
                employee=employee,
                basic_amount=basic_amount,
                allowances_amount=allowances_amount,
                overtime_amount=overtime_amount,
                deductions_amount=deductions_amount,
                net_pay=net_pay,
                days_worked=days_worked.quantize(Decimal("0.1")),
            )

            # [Gap #1] Auto-deduct approved advances from this slip
            from smart_agri.core.services.advances_service import AdvancesService
            advance_deducted = AdvancesService.deduct_advances_from_payroll(
                employee_id=employee.id, payroll_slip=slip,
            )
            net_pay = slip.net_pay  # Updated by deduction
            total_amount += net_pay

        run.total_amount = total_amount.quantize(Decimal("0.01"))
        run.created_by = user if getattr(user, 'is_authenticated', False) else None
        run.save(update_fields=["total_amount", "created_by"])
        return run

    @staticmethod
    @transaction.atomic
    def approve_run(run: PayrollRun, user):
        if run.status != PayrollStatus.DRAFT:
            raise ValidationError("Only Draft payroll runs can be approved.")

        # [AGRI-GUARDIAN] Fiscal Period Gate — AGENTS.md Axis 4
        from smart_agri.finance.services.core_finance import FinanceService
        FinanceService.check_fiscal_period(run.period_end, run.farm, strict=True)

        # [AGRI-GUARDIAN] Idempotency Guard — prevent duplicate postings on retry
        if FinancialLedger.objects.filter(
            farm=run.farm,
            account_code=FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
            description__contains=f"Payroll run {run.id}",
        ).exists():
            logger.info("Payroll run %s already posted to ledger; replay-safe skip.", run.id)
            run.status = PayrollStatus.APPROVED
            run.approved_at = timezone.now()
            run.approved_by = user if getattr(user, 'is_authenticated', False) else None
            run.save(update_fields=["status", "approved_at", "approved_by"])
            return run

        run.status = PayrollStatus.APPROVED
        run.approved_at = timezone.now()
        run.approved_by = user if getattr(user, 'is_authenticated', False) else None
        run.save(update_fields=["status", "approved_at", "approved_by"])

        amount = (run.total_amount or Decimal("0.00")).quantize(Decimal("0.0001"))
        created_by = user if getattr(user, "is_authenticated", False) else None

        # [AGRI-GUARDIAN] Double-Entry: Debit Labor Expense
        FinancialLedger.objects.create(
            farm=run.farm,
            cost_center=getattr(run.farm, 'cost_center', None),
            account_code=FinancialLedger.ACCOUNT_LABOR,
            debit=amount,
            credit=Decimal("0.0000"),
            description=f"مسير رواتب {run.id} - مصروف عمالة",
            created_by=created_by,
        )
        # [AGRI-GUARDIAN] Double-Entry: Credit Salaries Payable
        FinancialLedger.objects.create(
            farm=run.farm,
            cost_center=getattr(run.farm, 'cost_center', None),
            account_code=FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
            debit=Decimal("0.0000"),
            credit=amount,
            description=f"اعتماد مسير رواتب {run.id}",
            created_by=created_by,
        )

        # [Axis 9] Sovereign Liabilities — Zakat deduction on payroll
        from smart_agri.core.services.zakat_policy import ZAKAT_RATE_MAP
        zakat_rule = getattr(run.farm, 'zakat_rule', None)
        zakat_rate = ZAKAT_RATE_MAP.get(zakat_rule, Decimal("0.0000"))
        if zakat_rate > Decimal("0"):
            zakat_amount = (amount * zakat_rate).quantize(Decimal("0.0001"))
            # Debit: Zakat Expense
            FinancialLedger.objects.create(
                farm=run.farm,
                cost_center=getattr(run.farm, 'cost_center', None),
                account_code=FinancialLedger.ACCOUNT_ZAKAT_EXPENSE,
                debit=zakat_amount,
                credit=Decimal("0.0000"),
                description=f"زكاة رواتب — مسير #{run.id} ({zakat_rule} = {zakat_rate * 100}%)",
                created_by=created_by,
            )
            # Credit: Zakat Payable
            FinancialLedger.objects.create(
                farm=run.farm,
                cost_center=getattr(run.farm, 'cost_center', None),
                account_code=FinancialLedger.ACCOUNT_ZAKAT_PAYABLE,
                debit=Decimal("0.0000"),
                credit=zakat_amount,
                description=f"التزام زكاة — مسير #{run.id}",
                created_by=created_by,
            )
            logger.info("Zakat posted for payroll %s: %s (%s)", run.id, zakat_amount, zakat_rule)

        return run
