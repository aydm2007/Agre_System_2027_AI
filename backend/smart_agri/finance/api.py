"""
[AGRI-GUARDIAN] Finance API — Router Hub
════════════════════════════════════════

This module is the single entry-point for all Finance API viewsets.
All viewsets are imported from domain-specific sub-modules:

    api_ledger.py    → FinancialLedgerViewSet
    api_fiscal.py    → FiscalYearViewSet, FiscalPeriodViewSet
    api_expenses.py  → ActualExpenseViewSet, CostCenterViewSet
    api_treasury.py  → CashBoxViewSet, TreasuryTransactionViewSet
    api_approval.py  → ApprovalRuleViewSet, ApprovalRequestViewSet

URL routing is preserved: ``from smart_agri.finance.api import router``
"""
from rest_framework.routers import DefaultRouter

# ─── Domain Imports ──────────────────────────────────────────────────────────

from smart_agri.finance.api_ledger import (                      # noqa: F401
    FinancialLedgerViewSet,
    FinancialLedgerSerializer,
    LedgerFilter,
)
from smart_agri.finance.api_fiscal import (                      # noqa: F401
    FiscalYearViewSet,
    FiscalPeriodViewSet,
    FiscalYearSerializer,
    FiscalPeriodSerializer,
)
from smart_agri.finance.api_expenses import (                    # noqa: F401
    ActualExpenseViewSet,
    CostCenterViewSet,
    ActualExpenseSerializer,
    ActualExpenseFilter,
    CostCenterSerializer,
)
from smart_agri.finance.api_treasury import (                    # noqa: F401
    CashBoxViewSet,
    TreasuryTransactionViewSet,
)
from smart_agri.finance.api_approval import (                    # noqa: F401
    ApprovalRuleViewSet,
    ApprovalRequestViewSet,
    ApprovalRuleSerializer,
    ApprovalRequestSerializer,
)
from smart_agri.finance.api_petty_cash import (                  # noqa: F401
    PettyCashRequestViewSet,
    PettyCashSettlementViewSet,
)
from smart_agri.finance.api_supplier_settlement import (         # noqa: F401
    SupplierSettlementViewSet,
)

# ─── Router Registration ────────────────────────────────────────────────────

router = DefaultRouter()
router.register(r'ledger', FinancialLedgerViewSet, basename='ledger')
router.register(r'fiscal-years', FiscalYearViewSet, basename='fiscal-years')
router.register(r'fiscal-periods', FiscalPeriodViewSet, basename='fiscal-periods')
router.register(r'expenses', ActualExpenseViewSet, basename='expenses')
router.register(r'approval-rules', ApprovalRuleViewSet, basename='approval-rules')
router.register(r'approval-requests', ApprovalRequestViewSet, basename='approval-requests')
router.register(r'cashboxes', CashBoxViewSet, basename='cashboxes')
router.register(r'treasury-transactions', TreasuryTransactionViewSet, basename='treasury-transactions')
router.register(r'cost-centers', CostCenterViewSet, basename='cost-centers')
router.register(r'petty-cash-requests', PettyCashRequestViewSet, basename='petty-cash-requests')
router.register(r'petty-cash-settlements', PettyCashSettlementViewSet, basename='petty-cash-settlements')
router.register(r'supplier-settlements', SupplierSettlementViewSet, basename='supplier-settlements')
