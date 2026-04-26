"""
[AGRI-GUARDIAN] Finance API Split Roadmap
========================================

This module documents the planned extraction of finance/api.py (1223 lines)
into domain-specific viewset modules.

Current structure (api.py):
    Lines 1-48      : Imports
    Lines 49-165    : Serializers (CostCenter, Ledger, FiscalYear, FiscalPeriod)
    Lines 166-194   : Filters (LedgerFilter)
    Lines 200-412   : FinancialLedgerViewSet
    Lines 415-469   : FiscalYearViewSet
    Lines 472-651   : FiscalPeriodViewSet
    Lines 652-712   : ActualExpense Serializer + Filter
    Lines 715-853   : ActualExpenseViewSet
    Lines 864-962   : Treasury (CashBox + TreasuryTransactionViewSet)
    Lines 966-1006  : Approval Serializers
    Lines 1008-1167 : Approval Viewsets
    Lines 1168-1223 : AdvancedReport + Router registration

Planned extraction order (lowest risk first):
    1. Approval serializers + viewsets → api_approval.py
    2. Treasury viewsets → api_treasury.py
    3. Fiscal viewsets → api_fiscal.py
    4. Expense viewsets → api_expenses.py
    5. Ledger viewset → api_ledger.py

After extraction, api.py becomes a 50-line router-only file that imports
and registers each viewset from sub-modules.

Status: DEFERRED (no-regression mode active; these files are production-critical)
"""
