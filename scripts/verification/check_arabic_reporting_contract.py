#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
config = ROOT / 'frontend' / 'src' / 'config' / 'enterpriseArabicConfig.js'
component = ROOT / 'frontend' / 'src' / 'components' / 'analytics' / 'ArabicExecutiveKpiCards.jsx'
doc = ROOT / 'docs' / 'doctrine' / 'ARABIC_EXECUTIVE_REPORTING_V6.md'
for path in [config, component, doc]:
    if not path.exists():
        print(f'FAIL: missing Arabic reporting artifact {path.relative_to(ROOT)}')
        sys.exit(1)
text = config.read_text(encoding='utf-8')
for needle in ['locale', 'direction', 'executiveKpis', 'approvalLanes']:
    if needle not in text:
        print(f'FAIL: enterpriseArabicConfig missing {needle}')
        sys.exit(1)
print('PASS: V6 Arabic executive reporting contract present')
