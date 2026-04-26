#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
checks = [
    ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'decimal_guard.py',
    ROOT / 'backend' / 'smart_agri' / 'integrations' / 'services.py',
    ROOT / 'backend' / 'smart_agri' / 'finance' / 'services' / 'fiscal_fund_governance_service.py',
    ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'farm_tiering_policy_service.py',
    ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'harvest_compliance_service.py',
    ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'seasonal_settlement_service.py',
    ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'sharecropping_settlement_service.py',
    ROOT / 'backend' / 'smart_agri' / 'core' / 'services' / 'sovereign_zakat_service.py',
    ROOT / 'docs' / 'doctrine' / 'V8_FINAL_CLOSURE_MATRIX.md',
    ROOT / 'docs' / 'doctrine' / 'DOCX_CODE_TRACEABILITY_MATRIX_V8.md',
    ROOT / 'docs' / 'reports' / 'REMEDIATION_REGISTER_V8.md',
]
for path in checks:
    if not path.exists():
        print(f'FAIL: missing {path.relative_to(ROOT)}')
        sys.exit(1)
text = (ROOT / 'scripts' / 'verification' / 'generate_global_readiness_evidence_v8.py').read_text(encoding='utf-8')
if 'backend/scripts/check_no_float_mutations.py' not in text:
    print('FAIL: V8 evidence generator must call the strong float gate explicitly')
    sys.exit(1)
print('PASS: V8 enterprise closure contract is present')
