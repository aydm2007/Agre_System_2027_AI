#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python scripts/verification/check_bootstrap_contract.py
python scripts/verification/check_docx_traceability.py
python scripts/verification/check_enterprise_readiness.py
python scripts/verification/check_arabic_enterprise_contract.py
python scripts/verification/check_mandatory_expansion_contract.py
python scripts/verification/check_audit_event_factory_contract.py
python scripts/verification/check_multisite_offline_contract.py
python scripts/verification/check_arabic_reporting_contract.py
python scripts/verification/check_v6_expansion_contract.py
python scripts/verification/check_v7_fixed_assets_and_fuel.py
python scripts/verification/check_integrations_service_layer_writes.py
python scripts/verification/check_v8_enterprise_closure.py
python scripts/verification/check_v9_planning_enterprise_contract.py
python scripts/verification/check_v9_financial_enterprise_contract.py
python scripts/verification/check_v9_99_candidate.py
python scripts/verification/check_no_bare_exceptions.py
python scripts/verification/check_service_layer_writes.py
python scripts/verification/check_accounts_service_layer_writes.py
python scripts/verification/check_auth_service_layer_writes.py
python scripts/check_no_float_mutations.py
python scripts/check_idempotency_actions.py
python scripts/check_farm_scope_guards.py

echo "V8 Arabic enterprise static preflight passed. Runtime verification still required in a provisioned environment."

# Optional: generate evidence artifact (does not require runtime)
python scripts/verification/generate_global_readiness_evidence_v9.py || true
