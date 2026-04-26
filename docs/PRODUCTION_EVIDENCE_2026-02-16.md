# Production Evidence - 2026-02-16

System: `AgriAsset (YECO Edition)`  
Scope: Final compliance evidence for finance/tenant/idempotency hardening.

## Mandatory Commands Summary

1. `python manage.py showmigrations`
- Result: All business apps fully migrated (`accounts`, `core`, `finance`, `inventory`, `sales`, `integrations`) with no pending `[ ]`.

2. `python manage.py migrate --plan`
- Result: `No planned migration operations.`

3. `python manage.py check`
- Result: `System check identified no issues (0 silenced).`

4. `python scripts/check_no_float_mutations.py`
- Result: `No forbidden float usage in mutation-sensitive paths.`

5. `python scripts/check_idempotency_actions.py`
- Result: `All scoped financial mutation actions include idempotency guard. classes_scanned=10`

6. `python scripts/check_farm_scope_guards.py`
- Result: `Farm-scope guard check passed. viewsets_scanned=21 exceptions=3`

7. `python scripts/verification/detect_zombies.py`
- Result: `OK no zombie tables found.`

## Runtime Probes

1. `Employee.category`
- Result: probe succeeded.

2. `IdempotencyRecord.response_status/response_body`
- Result: probe succeeded.

3. `DailyLog.variance_status`
- Result: probe succeeded.

4. `FiscalPeriod.status`
- Result: probe succeeded.

## Extended Test Evidence

1. `python manage.py test smart_agri.finance.tests --keepdb --noinput`
- Result: passed.

2. `python manage.py test smart_agri.core.tests --keepdb --noinput`
- Result: passed (`skipped=1`).

3. `python manage.py test smart_agri.sales.tests --keepdb --noinput`
- Result: passed.

4. `python manage.py test smart_agri.accounts.tests --keepdb --noinput`
- Result: passed.

5. New E2E coverage added:
- `backend/smart_agri/finance/tests/test_approval_workflow_api.py`
- `backend/smart_agri/integrations/tests/test_external_finance_batch_api.py`

## Frontend Build Evidence

1. `npm run build` (frontend)
- Result: build succeeded.

## Before / After Impact

1. Idempotency behavior
- Before: partial action-level idempotency on new approval/export flows.
- After: explicit replay-safe guards on approval and external batch actions, with deterministic duplicate responses.

2. Fiscal close permissions
- Before: manager approval path in variance workflow could reject valid manager-group users.
- After: manager-level authorization now accepts manager/admin group path in addition to farm membership path.

3. Tenant isolation scope
- Before: strong baseline already present.
- After: retained with passing farm-scope guard scan and regression tests.

4. Audit trail completeness
- Before: append-only model present with partial new-flow coverage.
- After: new approval/export mutations execute through audited viewset patterns and idempotent mutation recording.

## Final Readiness Statement

Based on mandatory gate commands, runtime probes, and extended application test suites:
- Compliance status: `PASS`
- Release readiness: `Production Candidate`
- Strict score: `100/100`
> [!IMPORTANT]
> Historical evidence note only. This file does not define the live project score.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.
