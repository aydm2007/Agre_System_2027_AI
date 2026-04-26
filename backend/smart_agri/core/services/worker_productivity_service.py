"""
WorkerProductivityService — مؤشرات أداء العمال.

AGENTS.md Compliance:
  - §297-301: Required KPI Outputs (Per Farm)
    - Daily: labor cost variance
    - Weekly: budget burn vs plan
  - §139-144: HR Admin Segregation
  - Axis 5: Decimal, Surra-based
  - Axis 6: Farm-scoped queries (mandatory)
  - Service Layer Pattern
"""

import logging
from decimal import Decimal
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate

from smart_agri.core.models.hr import Employee, EmploymentCategory, Timesheet
from smart_agri.core.models.activity import Activity, ActivityEmployee

logger = logging.getLogger(__name__)

FOUR_DP = Decimal("0.0001")
ZERO = Decimal("0.0000")


class WorkerProductivityService:
    """
    [AGENTS.md §298] Daily and monthly labor KPI per farm.
    OFFICIAL employees: attendance-only metrics.
    CASUAL employees: productivity + cost metrics.
    """

    @staticmethod
    def get_labor_kpi(*, farm_id, date_from=None, date_to=None):
        """
        Main KPI endpoint — labor performance summary.

        Returns:
            dict with aggregated labor metrics
        """
        if not farm_id:
            return {"error": "[Axis 6] farm_id مطلوب"}

        # ── Base filters ─────────────────────────────────────────────
        ts_filter = Q(farm_id=farm_id, deleted_at__isnull=True)
        ae_filter = Q(
            activity__log__farm_id=farm_id,
            activity__deleted_at__isnull=True,
        )

        if date_from:
            ts_filter &= Q(date__gte=date_from)
            ae_filter &= Q(activity__log__log_date__gte=date_from)
        if date_to:
            ts_filter &= Q(date__lte=date_to)
            ae_filter &= Q(activity__log__log_date__lte=date_to)

        # ── 1. Timesheet aggregates ──────────────────────────────────
        ts_stats = Timesheet.objects.filter(ts_filter).aggregate(
            total_surrah=Sum('surrah_count'),
            total_overtime=Sum('surrah_overtime'),
            total_entries=Count('id'),
            approved_entries=Count('id', filter=Q(is_approved=True)),
            unique_employees=Count('employee_id', distinct=True),
        )

        # ── 2. ActivityEmployee aggregates ───────────────────────────
        ae_stats = ActivityEmployee.objects.filter(ae_filter).aggregate(
            total_registered=Count('id', filter=Q(labor_type='REGISTERED')),
            total_casual_batches=Count('id', filter=Q(labor_type='CASUAL_BATCH')),
            total_casual_workers=Sum(
                'workers_count',
                filter=Q(labor_type='CASUAL_BATCH'),
            ),
            total_wage_cost=Sum('wage_cost'),
        )

        # ── 3. Per-employee breakdown ────────────────────────────────
        employee_breakdown = Timesheet.objects.filter(ts_filter).values(
            'employee__id',
            'employee__first_name',
            'employee__last_name',
            'employee__category',
            'employee__shift_rate',
        ).annotate(
            surrah=Sum('surrah_count'),
            overtime=Sum('surrah_overtime'),
            days=Count('id'),
        ).order_by('-surrah')

        workers = []
        for row in employee_breakdown:
            surrah = row['surrah'] or Decimal('0.00')
            rate = row['employee__shift_rate'] or Decimal('0.0000')
            is_official = row['employee__category'] == EmploymentCategory.OFFICIAL

            workers.append({
                'employee_id': row['employee__id'],
                'name': f"{row['employee__first_name']} {row['employee__last_name']}",
                'category': row['employee__category'],
                'total_surrah': str(surrah),
                'total_overtime': str(row['overtime'] or Decimal('0.00')),
                'days': row['days'],
                'estimated_cost': '0.0000' if is_official else str(
                    (surrah * rate).quantize(FOUR_DP)
                ),
                'productivity_rank': 'N/A' if is_official else (
                    'عالية' if surrah >= Decimal('20') else
                    'متوسطة' if surrah >= Decimal('10') else
                    'منخفضة'
                ),
            })

        # ── 4. Daily trend ───────────────────────────────────────────
        daily_trend = Timesheet.objects.filter(ts_filter).values(
            day=TruncDate('date'),
        ).annotate(
            surrah=Sum('surrah_count'),
            workers=Count('employee_id', distinct=True),
        ).order_by('day')

        total_surrah = ts_stats['total_surrah'] or Decimal('0.00')
        total_entries = ts_stats['total_entries'] or 0
        unique_days = daily_trend.count()
        avg_surrah_per_day = (
            (total_surrah / Decimal(str(unique_days))).quantize(FOUR_DP)  # agri-guardian: decimal-safe
            if unique_days > 0 else ZERO
        )

        return {
            'summary': {
                'total_surrah': str(total_surrah),
                'total_overtime': str(ts_stats['total_overtime'] or Decimal('0.00')),
                'total_entries': total_entries,
                'approved_entries': ts_stats['approved_entries'] or 0,
                'approval_rate': str(
                    (Decimal(str(ts_stats['approved_entries'] or 0)) /  # agri-guardian: decimal-safe
                     Decimal(str(max(total_entries, 1))) * 100).quantize(Decimal('0.1'))
                ),
                'unique_employees': ts_stats['unique_employees'] or 0,
                'unique_days': unique_days,
                'avg_surrah_per_day': str(avg_surrah_per_day),
            },
            'activity_stats': {
                'registered_assignments': ae_stats['total_registered'] or 0,
                'casual_batches': ae_stats['total_casual_batches'] or 0,
                'casual_workers_total': str(ae_stats['total_casual_workers'] or Decimal('0.00')),
                'total_wage_cost': str(ae_stats['total_wage_cost'] or ZERO),
            },
            'workers': workers,
            'daily_trend': [
                {
                    'date': str(d['day']),
                    'surrah': str(d['surrah'] or Decimal('0.00')),
                    'workers': d['workers'],
                }
                for d in daily_trend
            ],
        }
