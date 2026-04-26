#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
req = [
    ROOT / "backend/smart_agri/core/services/planning_enterprise_service.py",
    ROOT / "backend/smart_agri/core/services/seasonal_settlement_service.py",
    ROOT / "backend/smart_agri/core/services/harvest_compliance_service.py",
    ROOT / "backend/smart_agri/core/services/farm_tiering_policy_service.py",
    ROOT / "docs/doctrine/V9_FINAL_CLOSURE_MATRIX.md",
]
for p in req:
    if not p.exists():
        print(f'FAIL: missing {p.relative_to(ROOT)}')
        sys.exit(1)
text = (ROOT / "backend/smart_agri/core/services/planning_enterprise_service.py").read_text(encoding="utf-8")
for token in ['readiness_snapshot', 'planning_readiness_score', 'SeasonalSettlementService', 'HarvestComplianceService']:
    if token not in text:
        print(f'FAIL: planning enterprise service missing token: {token}')
        sys.exit(1)
print('PASS: V9 planning enterprise contract is present')
