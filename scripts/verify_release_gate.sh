#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

RUN_RUNTIME_PROBES=1
RUN_FRONTEND=1

for arg in "$@"; do
  case "$arg" in
    --skip-runtime-probes) RUN_RUNTIME_PROBES=0 ;;
    --skip-frontend) RUN_FRONTEND=0 ;;
    *)
      echo "[ERROR] Unknown flag: $arg" >&2
      echo "Usage: $0 [--skip-runtime-probes] [--skip-frontend]" >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "$BACKEND_DIR/manage.py" ]]; then
  echo "[ERROR] backend/manage.py not found. Run from repository root." >&2
  exit 1
fi

run_cmd() {
  local label="$1"
  shift
  printf "\n==> %s\n" "$label"
  "$@"
}

RLS_BYPASS_PY='from django.db import connection
with connection.cursor() as c: c.execute("select set_config('\''app.user_id'\'','\''-1'\'',false)")
'

cd "$BACKEND_DIR"
run_cmd "Django migrations status" python manage.py showmigrations
run_cmd "Django migration plan" python manage.py migrate --plan
run_cmd "Django system checks" python manage.py check

cd "$ROOT_DIR"
run_cmd "Bootstrap/runtime contract" python scripts/verification/check_bootstrap_contract.py
run_cmd "Docx traceability matrix coverage" python scripts/verification/check_docx_traceability.py
run_cmd "Enterprise readiness static contract" python scripts/verification/check_enterprise_readiness.py
run_cmd "Float mutation scan" python scripts/check_no_float_mutations.py
run_cmd "Idempotency action scan" python scripts/check_idempotency_actions.py
run_cmd "Zombie table detection" python scripts/verification/detect_zombies.py
run_cmd "Ghost trigger detection" python scripts/verification/detect_ghost_triggers.py
run_cmd "Runtime financial integrity probe" python scripts/verification/check_financial_integrity_runtime.py
run_cmd "Zakat harvest trigger verification" python backend/scripts/check_zakat_harvest_triggers.py
run_cmd "Solar depreciation verification" python backend/scripts/check_solar_depreciation_logic.py
run_cmd "Zakat V2 temporal policy tests" python backend/manage.py test smart_agri.core.tests.test_zakat_policy_v2 --keepdb --noinput
run_cmd "Labor estimation API tests" python backend/manage.py test smart_agri.core.tests.test_labor_estimation_api --keepdb --noinput
run_cmd "Auth service-layer write gate" python scripts/verification/check_auth_service_layer_writes.py
run_cmd "Compliance docs completeness" python scripts/verification/check_compliance_docs.py
run_cmd "DR evidence freshness" python scripts/verification/check_backup_freshness.py
run_cmd "DR restore drill evidence" python scripts/verification/check_restore_drill_evidence.py
run_cmd "Frontend mojibake guard" python scripts/verification/check_mojibake_frontend.py

if [[ "$RUN_FRONTEND" -eq 1 ]]; then
  run_cmd "Frontend unit: Daily Log resources" npm --prefix frontend run test -- src/components/daily-log/__tests__/DailyLogResources.test.jsx --run
  run_cmd "Frontend unit: mode access" npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run
  run_cmd "E2E daily-log (workers=1)" npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1
  run_cmd "E2E financial_workflow (workers=1)" npm --prefix frontend run test:e2e -- tests/e2e/financial_workflow.spec.js --workers=1
  run_cmd "E2E sales_financial_lifecycle (workers=1)" npm --prefix frontend run test:e2e -- tests/e2e/sales_financial_lifecycle.spec.js --workers=1
  run_cmd "E2E finance (workers=1)" npm --prefix frontend run test:e2e -- tests/e2e/finance.spec.js --workers=1
fi

if [[ "$RUN_RUNTIME_PROBES" -eq 1 ]]; then
  cd "$BACKEND_DIR"
  run_cmd "Runtime probe: Employee.category" \
    python manage.py shell -c "$RLS_BYPASS_PY; from smart_agri.core.models.hr import Employee; print(list(Employee.objects.values_list('id','category')[:1]))"
  run_cmd "Runtime probe: IdempotencyRecord response cache fields" \
    python manage.py shell -c "$RLS_BYPASS_PY; from smart_agri.core.models.log import IdempotencyRecord; print(list(IdempotencyRecord.objects.values_list('id','response_status','response_body')[:1]))"
  run_cmd "Runtime probe: DailyLog variance_status" \
    python manage.py shell -c "$RLS_BYPASS_PY; from smart_agri.core.models.log import DailyLog; print(list(DailyLog.objects.values_list('id','variance_status')[:1]))"
  run_cmd "Runtime probe: FiscalPeriod.status" \
    python manage.py shell -c "$RLS_BYPASS_PY; from smart_agri.finance.models import FiscalPeriod; print(list(FiscalPeriod.objects.values_list('id','status')[:1]))"
  run_cmd "Runtime probe: Farm.tier" \
    python manage.py shell -c "$RLS_BYPASS_PY; from smart_agri.core.models import Farm; print(list(Farm.objects.values_list('id','tier')[:1]))"
  run_cmd "Runtime probe: RoleDelegation table" \
    python manage.py shell -c "$RLS_BYPASS_PY; from smart_agri.accounts.models import RoleDelegation; print('RoleDelegation table exists:', RoleDelegation.objects.model._meta.db_table)"
fi

printf "\n[SUCCESS] Release-gate verification completed.\n"
