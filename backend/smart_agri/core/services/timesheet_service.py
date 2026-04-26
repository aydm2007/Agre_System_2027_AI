"""
TimesheetService — خدمة إنشاء وإدارة سجلات الدوام.

AGENTS.md Compliance:
  - §139-144: HR Admin Segregation (Official=attendance, Casual=crop-cost)
  - Axis 3: Fiscal Period Gate on timesheet creation
  - Axis 5: Surra is the financial labor unit
  - Axis 6: farm_id mandatory on every transactional row
  - Axis 7: AuditLog for sensitive mutations
  - Financial Integrity Axiom 4: CASUAL_BATCH → no payroll identity expansion
  - Service Layer Pattern: Views never write DB directly
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from smart_agri.core.models.hr import Timesheet, Employee, EmploymentCategory

logger = logging.getLogger(__name__)


class TimesheetService:
    """
    [AGENTS.md Service Layer Pattern]
    All Timesheet mutations go through this service.
    """

    @staticmethod
    @transaction.atomic
    def create_from_activity(activity, actor=None):
        """
        Auto-create Timesheet entries from ActivityEmployee records.

        Rules (AGENTS.md §139-144):
          - REGISTERED employees → create Timesheet with surrah_share
          - CASUAL_BATCH entries → NO Timesheet (Financial Integrity Axiom 4)
          - OFFICIAL employees → attendance only (no cost capitalization)

        Args:
            activity: Activity instance with employee_details
            actor: User performing the action (for audit)

        Returns:
            list of created/updated Timesheet instances
        """
        farm = activity.log.farm
        log_date = activity.log.log_date
        created_timesheets = []

        for ae in activity.employee_details.filter(labor_type='REGISTERED'):
            if not ae.employee_id:
                continue

            timesheet, created = Timesheet.objects.update_or_create(
                employee=ae.employee,
                date=log_date,
                farm=farm,
                activity=activity,
                defaults={
                    'surrah_count': ae.surrah_share or Decimal('1.00'),
                    'surrah_overtime': Decimal('0.00'),
                },
            )
            created_timesheets.append(timesheet)

            if created:
                logger.info(
                    "Timesheet auto-created: employee=%s, farm=%s, date=%s, surrah=%.2f",
                    ae.employee, farm, log_date, ae.surrah_share,
                )

        return created_timesheets

    @staticmethod
    @transaction.atomic
    def record_manual_timesheet(
        *,
        employee_id: int,
        farm_id: int,
        date,
        surrah_count,
        surrah_overtime=None,
        activity=None,
        actor=None,
    ):
        """
        Manual Timesheet entry — used by Timesheet UI page.

        Validates:
          - Employee belongs to farm (Axis 6)
          - Surra values are Decimal (Axis 5)
          - Fiscal period is open (Axis 3)
          - No float contamination
        """
        surrah = Decimal(str(surrah_count))
        overtime = Decimal(str(surrah_overtime or '0.00'))

        if surrah <= Decimal('0'):
            raise ValidationError({"surrah_count": "عدد الصرات يجب أن يكون أكبر من صفر."})
        if overtime < Decimal('0'):
            raise ValidationError({"surrah_overtime": "الإضافي لا يمكن أن يكون سالباً."})

        try:
            employee = Employee.objects.get(
                pk=employee_id,
                farm_id=farm_id,
                is_active=True,
                deleted_at__isnull=True,
            )
        except Employee.DoesNotExist:
            raise ValidationError(
                {"employee_id": "[Axis 6] الموظف غير موجود أو لا ينتمي لهذه المزرعة."}
            )

        # [Axis 3] Fiscal Period Gate
        try:
            from smart_agri.finance.services.core_finance import FinanceService
            FinanceService.check_fiscal_period(date, employee.farm, strict=True)
        except ImportError:
            logger.warning("FinanceService not available for fiscal period check.")
        except ValidationError:
            raise

        timesheet, created = Timesheet.objects.update_or_create(
            employee=employee,
            date=date,
            farm_id=farm_id,
            defaults={
                'surrah_count': surrah,
                'surrah_overtime': overtime,
                'activity': activity,
            },
        )

        # [Axis 7] AuditLog
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='MANUAL_TIMESHEET',
            model='Timesheet',
            object_id=str(timesheet.id),
            actor=actor,
            new_payload={'employee': str(employee), 'date': str(date), 'surrah': str(surrah), 'overtime': str(overtime)},
        )

        logger.info(
            "Manual timesheet %s: employee=%s, farm=%s, date=%s, surrah=%.2f+%.2f",
            "created" if created else "updated",
            employee, farm_id, date, surrah, overtime,
        )

        return timesheet

    @staticmethod
    @transaction.atomic
    def approve_timesheet(timesheet_id: int, approver):
        """
        Maker-Checker approval for Timesheet.
        [Axis 7] Records who approved + AuditLog.
        """
        try:
            ts = Timesheet.objects.select_for_update().get(
                pk=timesheet_id, deleted_at__isnull=True,
            )
        except Timesheet.DoesNotExist:
            raise ValidationError({"timesheet_id": "سجل الدوام غير موجود."})

        if ts.is_approved:
            return ts  # Idempotent — already approved

        ts.is_approved = True
        ts.approved_by = approver
        ts.save(update_fields=['is_approved', 'approved_by'])

        # [Axis 7] AuditLog
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='APPROVE_TIMESHEET',
            model='Timesheet',
            object_id=str(ts.id),
            actor=approver,
            new_payload={'employee': str(ts.employee), 'date': str(ts.date)},
        )

        logger.info(
            "Timesheet approved: id=%s, employee=%s, approver=%s",
            ts.id, ts.employee, approver,
        )
        return ts

    @staticmethod
    def get_monthly_summary(farm_id: int, year: int, month: int):
        """
        Monthly attendance summary for a farm.
        [Axis 6] Farm-scoped query.
        [Axis 5] All values as Decimal strings.
        [Axis 9] Budget burn calculation (§298).
        """
        from django.db.models import Sum, Count, Q

        timesheets = Timesheet.objects.filter(
            farm_id=farm_id,
            date__year=year,
            date__month=month,
            deleted_at__isnull=True,
        )

        summary = timesheets.values(
            'employee__id',
            'employee__first_name',
            'employee__last_name',
            'employee__employee_id',
            'employee__category',
            'employee__shift_rate',
        ).annotate(
            total_surrah=Sum('surrah_count'),
            total_overtime=Sum('surrah_overtime'),
            days_count=Count('id'),
            approved_count=Count('id', filter=Q(is_approved=True)),
        ).order_by('employee__last_name')

        results = []
        total_labor_cost = Decimal('0.0000')
        for row in summary:
            total_surrah = row['total_surrah'] or Decimal('0.00')
            shift_rate = row['employee__shift_rate'] or Decimal('0.0000')
            is_official = row['employee__category'] == EmploymentCategory.OFFICIAL

            estimated_cost = Decimal('0.0000') if is_official else (
                total_surrah * shift_rate
            ).quantize(Decimal('0.0001'))
            total_labor_cost += estimated_cost

            results.append({
                'employee_id': row['employee__id'],
                'employee_name': f"{row['employee__first_name']} {row['employee__last_name']}",
                'badge': row['employee__employee_id'],
                'category': row['employee__category'],
                'total_surrah': str(total_surrah),
                'total_overtime': str(row['total_overtime'] or Decimal('0.00')),
                'days_count': row['days_count'],
                'approved_count': row['approved_count'],
                'estimated_cost': str(estimated_cost),
            })

        # [Gap #9] Budget burn calculation
        budget_info = TimesheetService._get_labor_budget_burn(
            farm_id=farm_id, year=year, month=month, actual_cost=total_labor_cost,
        )

        return {
            'employees': results,
            'total_labor_cost': str(total_labor_cost),
            'budget': budget_info,
        }

    @staticmethod
    def _get_labor_budget_burn(*, farm_id, year, month, actual_cost):
        """
        [§298] Calculate budget burn vs plan for labor.
        """
        from smart_agri.core.models.planning import Budget
        budget = Budget.objects.filter(
            farm_id=farm_id,
            budget_year=year,
            deleted_at__isnull=True,
        ).first()

        if budget:
            monthly_budget = (budget.total_amount / Decimal('12')).quantize(Decimal('0.0001'))  # agri-guardian: decimal-safe
            burn_pct = (
                (actual_cost / monthly_budget * Decimal('100')).quantize(Decimal('0.1'))  # agri-guardian: decimal-safe
                if monthly_budget > 0 else Decimal('0.0')
            )

            # [Axis 8] Auto-create VarianceAlert if burn > 80%
            if burn_pct > Decimal('80.0'):
                from smart_agri.core.models.report import VarianceAlert
                VarianceAlert.objects.get_or_create(
                    farm_id=farm_id,
                    alert_type='LABOR_BUDGET_OVERRUN',
                    defaults={
                        'message': f"تجاوز ميزانية العمالة: {burn_pct}% من الميزانية الشهرية "
                                   f"({actual_cost}/{monthly_budget})",
                        'severity': 'WARNING' if burn_pct <= Decimal('100') else 'CRITICAL',
                    },
                )

            return {
                'monthly_budget': str(monthly_budget),
                'actual_cost': str(actual_cost),
                'burn_percentage': str(burn_pct),
                'status': 'CRITICAL' if burn_pct > 100 else 'WARNING' if burn_pct > 80 else 'OK',
            }

        return {
            'monthly_budget': '0.0000',
            'actual_cost': str(actual_cost),
            'burn_percentage': '0.0',
            'status': 'NO_BUDGET',
        }
