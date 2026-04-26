#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)

# Fixed assets service
fa_service = ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'fixed_asset_lifecycle_service.py'
if not fa_service.exists():
    fail('missing fixed_asset_lifecycle_service.py')

fa_text = fa_service.read_text(encoding='utf-8')
for needle in ['class FixedAssetLifecycleService', 'def capitalize_asset', 'def dispose_asset', 'AuditEventFactory', 'FinancialLedger']:
    if needle not in fa_text:
        fail(f'fixed assets lifecycle missing: {needle}')

# API actions
farm_viewset = ROOT / 'backend' / 'smart_agri' / 'core' / 'api' / 'viewsets' / 'farm.py'
api_text = farm_viewset.read_text(encoding='utf-8')
for needle in ["url_path='capitalize'", "url_path='dispose'", 'FixedAssetLifecycleService']:
    if needle not in api_text:
        fail(f'AssetViewSet missing: {needle}')

# Fuel reconciliation posting service
fuel_service = ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'fuel_reconciliation_posting_service.py'
if not fuel_service.exists():
    fail('missing fuel_reconciliation_posting_service.py')

fuel_text = fuel_service.read_text(encoding='utf-8')
for needle in ['approve_and_post', 'ACCOUNT_FUEL_EXPENSE', 'ACCOUNT_FUEL_INVENTORY', 'AuditEventFactory']:
    if needle not in fuel_text:
        fail(f'fuel reconciliation posting missing: {needle}')

# Fuel reconciliation API action
fuel_view = ROOT / 'backend' / 'smart_agri' / 'core' / 'views' / 'fuel_reconciliation_dashboard.py'
view_text = fuel_view.read_text(encoding='utf-8')
for needle in ['post-reconciliation', 'FuelReconciliationPostingService']:
    if needle not in view_text:
        fail(f'fuel reconciliation viewset missing: {needle}')

# Docs
closure = ROOT / 'docs' / 'doctrine' / 'V7_CLOSURE_NOTES.md'
if not closure.exists():
    fail('missing docs/doctrine/V7_CLOSURE_NOTES.md')

print('PASS: V7 fixed assets + fuel reconciliation closure contract is present')
