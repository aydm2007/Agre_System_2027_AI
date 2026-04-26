#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

farm_vset = ROOT / 'backend' / 'smart_agri' / 'core' / 'api' / 'viewsets' / 'farm.py'
fuel_vset = ROOT / 'backend' / 'smart_agri' / 'core' / 'views' / 'fuel_reconciliation_dashboard.py'
fa_service = ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'fixed_asset_lifecycle_service.py'
fuel_service = ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'fuel_reconciliation_posting_service.py'

missing = [p for p in [farm_vset, fuel_vset, fa_service, fuel_service] if not p.exists()]
if missing:
    print('FAIL: missing V7 workflow artifacts:')
    for p in missing:
        print('-', p)
    sys.exit(1)

farm_text = farm_vset.read_text(encoding='utf-8')
for needle in ["url_path='capitalize'", "url_path='dispose'", 'FixedAssetLifecycleService']:
    if needle not in farm_text:
        print(f'FAIL: farm.py missing {needle}')
        sys.exit(1)

fuel_text = fuel_vset.read_text(encoding='utf-8')
for needle in ['post-reconciliation', 'FuelReconciliationPostingService']:
    if needle not in fuel_text:
        print(f'FAIL: fuel reconciliation view missing {needle}')
        sys.exit(1)

print('PASS: V7 fixed assets + fuel reconciliation workflow contracts present')
