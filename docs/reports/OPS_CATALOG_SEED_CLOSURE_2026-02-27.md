# OPS Catalog Seed Closure Report (2026-02-27)

## Scope
- Close schema drift for `supported_tasks` m2m.
- Add reproducible seed command for operational crop catalog and plans.
- Validate baseline compliance gates before local commit.
- No business-logic change in finance/ledger paths.

## Implemented Changes
1. Schema drift fix:
- Added migration: `backend/smart_agri/core/migrations/0059_restore_crop_supported_tasks_m2m.py`
- Behavior:
  - Creates `core_crop_supported_tasks` if missing.
  - Adds required indexes.
  - Backfills links from `core_task.crop_id` using `ON CONFLICT DO NOTHING`.

2. Reproducible operational seed:
- Added command: `python backend/manage.py seed_operational_catalog`
- File: `backend/smart_agri/core/management/commands/seed_operational_catalog.py`
- Options:
  - `--clean-ops` (default: true)
  - `--no-clean-ops`
  - `--season <year>`
  - `--dry-run`

3. Install docs update:
- Updated `README_Install.md` with `seed_operational_catalog` usage and options.

## Verification Commands and Results
### Schema/Health
- `python backend/manage.py showmigrations` => PASS (all apps fully migrated, including `core.0059`).
- `python backend/manage.py migrate --plan` => PASS (`No planned migration operations`).
- `python backend/manage.py check` => PASS (`0 issues`).

### Compliance Safety (AGENTS mandatory subset)
- `python scripts/check_idempotency_actions.py` => PASS
- `python scripts/check_no_float_mutations.py` => PASS

### Frontend guard
- `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run` => PASS (3/3)

### Reproducibility test (seed run twice)
- `python backend/manage.py seed_operational_catalog --clean-ops` => PASS
- second run same command => PASS (no integrity error)

## DB Probe (post-seed)
Command:
- `python backend/manage.py shell -c "..."`

Result:
- `active_crops=5`
- `mango_varieties=['قلب الثور','التيمور','الزبدة','السوداني']`
- `banana_varieties=['موز درجة اولى']`
- `task_counts` per crop = 5 each
- `active_plans=10`

## Before/After Summary
### Before
- Missing physical m2m table `core_crop_supported_tasks` caused runtime failure when setting `crop.supported_tasks`.
- Operational seeding existed only as manual DB actions (not codified).

### After
- Drift closed by migration `0059`.
- Operational crop/task/template/plan generation is codified in a reusable management command.
- Seed execution is repeatable under `--clean-ops` and verifiable with deterministic outputs.

## Boundaries
- No direct UPDATE/DELETE on immutable financial ledger rows.
- No API contract changes for finance/sales endpoints.
- E2E full suite intentionally out of this closure scope.
