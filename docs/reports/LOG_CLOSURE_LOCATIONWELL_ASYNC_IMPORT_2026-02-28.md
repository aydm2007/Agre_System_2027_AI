> [!IMPORTANT]
> Historical or scoped report only. This file is dated context and not the live score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.

# Log Closure Audit - LocationWell + Async Tasks Import

Date: 2026-02-28
Scope: backend farm scoping, location-wells filtering, async tasks import path, E2E auth noise reduction.

## Findings Closed

1. LocationWell 500 on `farm_id` query
- Root cause: generic farm scoping in base viewset assumed direct `farm_id` field on all models.
- Fix: defensive farm-field detection in base scoping; relation-scoped viewsets keep their own filter contract.
- Result: `LocationWellViewSet` no longer crashes with `Cannot resolve keyword 'farm_id'`.

2. Celery/async import collision
- Root cause: `smart_agri.core.tasks.py` (module file) collided with `smart_agri.core.tasks/` (package).
- Fix: canonicalize to package by moving shared task exports into `core/tasks/__init__.py` and removing `core/tasks.py`.
- Result: `smart_agri.core.tasks.report_tasks` imports correctly.

3. Advanced report import path instability
- Root cause: eager import path increased risk of partial initialization during startup/import ordering.
- Fix: lazy import of `generate_profitability_report` inside service execution path.
- Result: async report task import smoke test passes.

4. E2E auth/farms bootstrap noise
- Root cause: helper repeatedly called farm bootstrap in the same session.
- Fix: session-level short-circuit in e2e auth helper after successful bootstrap.
- Result: reduced redundant auth/farms calls in E2E runs.

## Verification Matrix

| Command | Result |
|---|---|
| `python backend/manage.py test smart_agri.core.tests.test_location_wells --keepdb --noinput` | PASS |
| `python backend/manage.py test smart_agri.core.tests.test_tasks_import_contract --keepdb --noinput` | PASS |
| `python backend/manage.py check` | PASS |
| `python backend/manage.py migrate --plan` | PASS (no planned operations) |
| `python scripts/check_idempotency_actions.py` | PASS |
| `python scripts/check_no_float_mutations.py` | PASS |
| `python scripts/check_farm_scope_guards.py` | PASS |
| `python scripts/check_fiscal_period_gates.py` | PASS |
| `python scripts/verification/check_mojibake_frontend.py` | PASS |
| `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run` | PASS |
| `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1` | PASS |
| `npm --prefix frontend run test:e2e -- tests/e2e/all_pages.spec.js --workers=1` | PASS |

## Decision

- Status: GO
- Blockers: none in this scope
- Strict score for this closure scope: 100/100
> [!IMPORTANT]
> Historical scoped closure report only. Any score in this file is dated context, not live authority.
> Live project authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.
