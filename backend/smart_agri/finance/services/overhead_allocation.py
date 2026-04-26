import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Sum
from smart_agri.finance.models import FinancialLedger
from smart_agri.core.models.planning import CropPlan
from smart_agri.core.constants import CropPlanStatus
from rest_framework.exceptions import ValidationError

class OverheadAllocationService:
    """
    [AGRI-GUARDIAN Phase 6] Automated Overhead Allocation (Activity-Based Costing)
    Distributes unallocated overhead expenses (like admin, electricity) across active
    crop plans based on their relative land area.
    """

    @staticmethod
    @transaction.atomic
    def allocate_indirect_expenses(farm, period_start, period_end, user=None, ref_id=""):
        # 1. Calculate unallocated balance in 4001-EXP-ADMIN
        expenses = FinancialLedger.objects.filter(
            farm=farm,
            account_code=FinancialLedger.ACCOUNT_EXPENSE_ADMIN,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end,
            is_posted=True
        ).aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )

        total_debit = expenses.get('total_debit') or Decimal('0.0000')
        total_credit = expenses.get('total_credit') or Decimal('0.0000')
        balance_to_allocate = total_debit - total_credit

        if balance_to_allocate <= 0:
            return []

        # 2. Identify active crop plans with defined area
        active_plans = CropPlan.objects.filter(
            farm=farm,
            status=CropPlanStatus.ACTIVE,
            area__gt=0
        )

        if not active_plans.exists():
            raise ValidationError("لا توجد خطط محاصيل نشطة بمساحات محددة لتوزيع التكاليف العامة عليها.")

        total_area = sum(plan.area for plan in active_plans)

        allocations = []
        precision = Decimal('0.0001')
        allocated_so_far = Decimal('0.0000')

        plans_list = list(active_plans)

        # 3. Distribute balance proportionally
        for i, plan in enumerate(plans_list):
            if i == len(plans_list) - 1:
                # The last plan absorbs any rounding tail
                share = balance_to_allocate - allocated_so_far
            else:
                share = (Decimal(str(plan.area)) / Decimal(str(total_area)) * balance_to_allocate).quantize(precision, rounding=ROUND_HALF_UP)  # agri-guardian: decimal-safe
                allocated_so_far += share

            if share <= 0:
                continue

            # Debit 1400-WIP for each plan
            dr_entry = FinancialLedger.objects.create(
                farm=farm,
                account_code=FinancialLedger.ACCOUNT_WIP,
                debit=share,
                credit=Decimal('0.0000'),
                description=f"توزيع نفقات عامة للمحصول - {plan.name} {ref_id}",
                crop_plan=plan,
                created_by=user,
                is_posted=False  # Respect Maker-Checker workflow
            )
            allocations.append(dr_entry)

        # 4. Credit 4001-EXP-ADMIN to zero it out for the period
        cr_entry = FinancialLedger.objects.create(
            farm=farm,
            account_code=FinancialLedger.ACCOUNT_EXPENSE_ADMIN,
            debit=Decimal('0.0000'),
            credit=balance_to_allocate,
            description=f"إغلاق وتوزيع النفقات العامة على المحاصيل {ref_id}",
            created_by=user,
            is_posted=False  # Respect Maker-Checker workflow
        )
        allocations.append(cr_entry)

        return allocations
