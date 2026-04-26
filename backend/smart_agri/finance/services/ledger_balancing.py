"""
[AGRI-GUARDIAN §3] Auto-Balancing Validation Service.
Validates the double-entry accounting equation per farm.
"""
import logging
from decimal import Decimal
from typing import Optional
from django.db.models import Sum

try:
    from smart_agri.finance.models import FinancialLedger
except ImportError:  # pragma: no cover - import patched in tests or resolved at runtime
    FinancialLedger = None

logger = logging.getLogger(__name__)


class LedgerBalancingService:
    """
    [AGRI-GUARDIAN §3] Fiscal Lifecycle: Auto-Balancing Validation
    Ensures that for a given farm and fiscal period, the total Debits equal total Credits.
    If an imbalance is detected, an alert is raised to the financial controller dashboard.

    [Axis 6] Tenant Isolation: farm_id is mandatory — zero global queries.
    """

    @staticmethod
    def validate_balances(farm_id: Optional[int] = None, fiscal_period_id: Optional[int] = None) -> bool:
        """
        Validates the fundamental accounting equation: SUM(Debit) == SUM(Credit)
        Returns True if balanced, False if an imbalance is found.
        
        [Axis 6] farm_id is mandatory for tenant isolation.
        If not provided, raises ValueError to prevent global queries.
        """
        ledger_model = FinancialLedger
        if ledger_model is None:  # pragma: no cover - runtime fallback if import order is incomplete
            from smart_agri.finance.models import FinancialLedger as ledger_model

        if farm_id is None:
            raise ValueError(
                "[Axis 6] farm_id is mandatory for validate_balances(). "
                "Zero global queries allowed per AGENTS.md §151."
            )

        qs = ledger_model.objects.filter(farm_id=farm_id)

        if fiscal_period_id:
            qs = qs.filter(fiscal_period_id=fiscal_period_id)
            
        # If no ledger entries exist, it is balanced by definition.
        if not qs.exists():
            return True

        totals = qs.aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        
        total_debit = totals['total_debit'] or Decimal("0.0000")
        total_credit = totals['total_credit'] or Decimal("0.0000")
        
        variance = abs(total_debit - total_credit)
        
        if variance > Decimal("0.0000"):
            logger.critical(
                f"[LEDGER IMBALANCE DETECTED] Farm={farm_id} Period={fiscal_period_id} "
                f"Debit={total_debit} Credit={total_credit} Variance={variance}"
            )
            LedgerBalancingService._raise_variance_alert(farm_id, fiscal_period_id, variance, total_debit, total_credit)
            return False
            
        logger.info(f"Ledger is balanced for Farm={farm_id} Period={fiscal_period_id}. Total={total_debit}.")
        return True

    @staticmethod
    def _raise_variance_alert(farm_id: int, period_id: Optional[int], variance: Decimal, debits: Decimal, credits: Decimal):
        """Creates a high-priority variance alert for the financial controller."""
        from smart_agri.core.models.farm import Farm
        from smart_agri.core.models.report import VarianceAlert

        farm = Farm.objects.filter(id=farm_id).first() if farm_id else None
        
        alert_msg = (
            f"⚠️ خطأ حرج في التوازن المالي ⚠️\n"
            f"إجمالي المدين: {debits}\n"
            f"إجمالي الدائن: {credits}\n"
            f"الفارق: {variance}\n\n"
            "هذا يشير إلى خلل محاسبي يتطلب مراجعة فورية لسجل القيود المزدوجة."
        )
        
        if period_id:
             alert_msg += f"\nالفترة المالية المتأثرة: {period_id}"
             
        # Create an Alert if Farm is known
        if farm:
            VarianceAlert.objects.create(
                farm=farm,
                category=VarianceAlert.CATEGORY_OTHER,
                activity_name="Auto-Balancing Validation",
                alert_message=alert_msg,
                variance_amount=variance,
                variance_percentage=Decimal("100.00") # High severity 
            )
