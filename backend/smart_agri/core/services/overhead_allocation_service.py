"""
OverheadAllocationService — التوزيع الآلي للنفقات العامة.

Allocates indirect overhead expenses (electricity, security, admin salaries)
to active CropPlans based on their area ratio.

Flow:
  1. Sum all unallocated ACCOUNT_OVERHEAD ledger entries for [farm, month]
  2. Read active CropPlans with area > 0
  3. Calculate each plan's area share
  4. Post allocation entries: DR WIP (per plan), CR OVERHEAD

AGENTS.md Compliance:
  - Axis 2: Idempotency via description-based duplicate guard
  - Axis 4: Fund Accounting — proper double-entry
  - Axis 5: Decimal(19,4)
  - Axis 6: Farm-scoped
  - Axis 7: AuditLog
"""

import logging
from decimal import Decimal
from datetime import date

from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

FOUR_DP = Decimal("0.0001")
ZERO = Decimal("0.0000")


class OverheadAllocationService:
    """
    [AGENTS.md] Automated overhead cost allocation to crop plans.
    Distributes farm-level indirect costs proportionally by cultivated area.
    """

    @staticmethod
    @transaction.atomic
    def allocate_monthly_overhead(*, farm_id, year, month, actor=None):
        """
        Allocate all unallocated overhead for a farm/month to active CropPlans.

        Returns dict with allocation details.
        Raises ValidationError if no active plans or no overhead to allocate.
        """
        from smart_agri.finance.models import FinancialLedger
        from smart_agri.core.models.planning import CropPlan
        from smart_agri.core.constants import CropPlanStatus

        if not farm_id:
            raise ValidationError({"farm_id": "[Axis 6] معرف المزرعة مطلوب."})

        # [Axis 2] Idempotency — check if already allocated for this period
        alloc_marker = f"overhead-alloc-{farm_id}-{year}-{month:02d}"
        if FinancialLedger.objects.filter(
            farm_id=farm_id,
            account_code=FinancialLedger.ACCOUNT_WIP,
            description__contains=alloc_marker,
        ).exists():
            logger.info("Overhead already allocated for %s/%s (farm=%s). Idempotent skip.", year, month, farm_id)
            return {"status": "already_allocated", "period": f"{year}-{month:02d}"}

        # 1. Sum unallocated overhead debits for the month
        from django.db.models.functions import TruncMonth
        overhead_total = FinancialLedger.objects.filter(
            farm_id=farm_id,
            account_code=FinancialLedger.ACCOUNT_OVERHEAD,
            created_at__year=year,
            created_at__month=month,
        ).aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
        )
        raw_debit = overhead_total['total_debit'] or ZERO
        raw_credit = overhead_total['total_credit'] or ZERO
        net_overhead = (raw_debit - raw_credit).quantize(FOUR_DP)

        if net_overhead <= ZERO:
            return {"status": "no_overhead", "net_overhead": str(net_overhead)}

        # 2. Get active CropPlans with area > 0
        active_plans = CropPlan.objects.filter(
            farm_id=farm_id,
            status=CropPlanStatus.ACTIVE,
            deleted_at__isnull=True,
            area__gt=0,
        ).values('id', 'name', 'area', 'crop__name')

        if not active_plans:
            raise ValidationError({
                "crop_plans": "لا توجد خطط زراعية نشطة بمساحة > 0 للتوزيع."
            })

        # 3. Calculate area ratios
        total_area = sum(p['area'] for p in active_plans)
        if total_area <= 0:
            raise ValidationError({"area": "إجمالي المساحة = 0."})

        allocations = []
        remaining = net_overhead
        plans_list = list(active_plans)

        created_by = actor if actor and getattr(actor, 'is_authenticated', False) else None

        for i, plan in enumerate(plans_list):
            area_ratio = Decimal(str(plan['area'])) / Decimal(str(total_area))  # agri-guardian: decimal-safe

            # Last plan gets the remainder to avoid rounding drift
            if i == len(plans_list) - 1:
                amount = remaining.quantize(FOUR_DP)
            else:
                amount = (net_overhead * area_ratio).quantize(FOUR_DP)
                remaining -= amount

            plan_label = f"{plan['crop__name'] or ''} — {plan['name']}"

            # 4. Post double-entry: DR WIP (for this plan), CR Overhead
            FinancialLedger.objects.create(
                farm_id=farm_id,
                account_code=FinancialLedger.ACCOUNT_WIP,
                debit=amount,
                credit=ZERO,
                description=(
                    f"توزيع نفقات عامة → {plan_label} "
                    f"({area_ratio * 100:.1f}% من {total_area} هكتار) "
                    f"[{alloc_marker}]"
                ),
                created_by=created_by,
            )
            FinancialLedger.objects.create(
                farm_id=farm_id,
                account_code=FinancialLedger.ACCOUNT_OVERHEAD,
                debit=ZERO,
                credit=amount,
                description=(
                    f"تحميل نفقات عامة ← {plan_label} "
                    f"[{alloc_marker}]"
                ),
                created_by=created_by,
            )

            allocations.append({
                "crop_plan_id": plan['id'],
                "crop_plan_name": plan_label,
                "area": str(plan['area']),
                "area_pct": f"{area_ratio * 100:.1f}%",
                "amount": str(amount),
            })

        # [Axis 7] AuditLog
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='OVERHEAD_ALLOCATION',
            model='FinancialLedger',
            object_id=alloc_marker,
            actor=actor,
            new_payload={
                'period': f"{year}-{month:02d}",
                'total_overhead': str(net_overhead),
                'plans_count': len(allocations),
            },
        )

        logger.info(
            "Overhead allocated: farm=%s, period=%s-%02d, total=%s, plans=%d",
            farm_id, year, month, net_overhead, len(allocations),
        )

        return {
            "status": "allocated",
            "period": f"{year}-{month:02d}",
            "total_overhead": str(net_overhead),
            "total_area": str(total_area),
            "allocations": allocations,
        }
