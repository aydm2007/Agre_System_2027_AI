"""
Financial Integrity Service — Core Proxy.

[AGRI-GUARDIAN] This module delegates to the canonical implementation in
``smart_agri.finance.services.financial_integrity_service``.

The canonical service lives in ``finance/`` because it depends on finance models
(ActualExpense, FinancialLedger, FiscalPeriod). This file re-exports the key
utilities so existing ``core/`` consumers don't break.

See: AGENTS.md Axis 4 (Fund Accounting) — Single Source of Truth.
"""
from smart_agri.finance.services.financial_integrity_service import (  # noqa: F401
    FinancialIntegrityService,
    FinancialIntegrityError,
)

__all__ = [
    "FinancialIntegrityService",
    "FinancialIntegrityError",
]
