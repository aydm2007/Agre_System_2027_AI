#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
req = [
    ROOT / "backend/smart_agri/finance/services/enterprise_financial_readiness_service.py",
    ROOT / "backend/smart_agri/finance/services/fiscal_fund_governance_service.py",
    ROOT / "backend/smart_agri/core/services/sharecropping_settlement_service.py",
    ROOT / "backend/smart_agri/core/services/sovereign_zakat_service.py",
]
for p in req:
    if not p.exists():
        print(f'FAIL: missing {p.relative_to(ROOT)}')
        sys.exit(1)
text = (ROOT / "backend/smart_agri/finance/services/enterprise_financial_readiness_service.py").read_text(encoding="utf-8")
for token in ['readiness_snapshot', 'financial_readiness_score', 'FiscalFundGovernanceService', 'SovereignZakatService']:
    if token not in text:
        print(f'FAIL: financial enterprise service missing token: {token}')
        sys.exit(1)
print('PASS: V9 financial enterprise contract is present')
