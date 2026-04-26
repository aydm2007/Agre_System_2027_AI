"""
AttendanceReportService — تقرير حضور شهري.

AGENTS.md Compliance:
  - §139-144: OFFICIAL = attendance only, CASUAL = crop cost
  - Axis 5: Surra-based
  - Axis 6: Farm-scoped
"""

import logging
from decimal import Decimal
from datetime import date, timedelta
from calendar import monthrange
from django.db.models import Sum, Count, Q, F

from smart_agri.core.models.hr import Employee, EmploymentCategory, Timesheet

logger = logging.getLogger(__name__)


class AttendanceReportService:
    """
    [AGENTS.md §298] Monthly attendance calendar grid.
    Builds a per-employee, per-day matrix for a given month.
    """

    @staticmethod
    def get_monthly_calendar(*, farm_id, year, month):
        """
        Returns a list of employee attendance records with daily breakdown.

        [Axis 6] Farm-scoped.
        [Axis 5] Surra values for each day.

        Returns:
            list[dict] with employee info + daily attendance array
        """
        if not farm_id:
            return []

        days_in_month = monthrange(year, month)[1]
        start = date(year, month, 1)
        end = date(year, month, days_in_month)

        # Get all active employees for this farm
        employees = Employee.objects.filter(
            farm_id=farm_id,
            is_active=True,
            deleted_at__isnull=True,
        ).order_by('category', 'first_name')

        # Get all timesheets for the period
        timesheets = Timesheet.objects.filter(
            farm_id=farm_id,
            date__gte=start,
            date__lte=end,
            deleted_at__isnull=True,
        ).select_related('employee')

        # Build lookup: {employee_id: {day_number: {surrah, overtime, approved}}}
        ts_lookup = {}
        for ts in timesheets:
            emp_id = ts.employee_id
            day = ts.date.day
            if emp_id not in ts_lookup:
                ts_lookup[emp_id] = {}
            ts_lookup[emp_id][day] = {
                'surrah': str(ts.surrah_count),
                'overtime': str(ts.surrah_overtime),
                'approved': ts.is_approved,
            }

        results = []
        for emp in employees:
            days_data = []
            total_surrah = Decimal('0.00')
            total_days = 0
            approved_count = 0

            for day_num in range(1, days_in_month + 1):
                day_entry = ts_lookup.get(emp.id, {}).get(day_num)
                if day_entry:
                    surrah = Decimal(day_entry['surrah'])
                    total_surrah += surrah
                    total_days += 1
                    if day_entry['approved']:
                        approved_count += 1
                    days_data.append({
                        'day': day_num,
                        'status': 'present',
                        'surrah': day_entry['surrah'],
                        'overtime': day_entry['overtime'],
                        'approved': day_entry['approved'],
                    })
                else:
                    # Check if this is a weekend (Friday)
                    d = date(year, month, day_num)
                    is_weekend = d.weekday() == 4  # Friday
                    days_data.append({
                        'day': day_num,
                        'status': 'weekend' if is_weekend else 'absent',
                        'surrah': '0.00',
                        'overtime': '0.00',
                        'approved': False,
                    })

            results.append({
                'employee_id': emp.id,
                'name': f"{emp.first_name} {emp.last_name}".strip(),
                'employee_number': emp.employee_id,
                'category': emp.category,
                'days_in_month': days_in_month,
                'total_surrah': str(total_surrah),
                'total_present': total_days,
                'total_absent': days_in_month - total_days,
                'approved_count': approved_count,
                'attendance_rate': str(
                    (Decimal(str(total_days)) / Decimal(str(days_in_month)) * 100).quantize(Decimal('0.1'))  # agri-guardian: decimal-safe
                ) if days_in_month > 0 else '0.0',
                'days': days_data,
            })

        return {
            'farm_id': farm_id,
            'year': year,
            'month': month,
            'days_in_month': days_in_month,
            'employees_count': len(results),
            'employees': results,
        }
