> [!IMPORTANT]
> Historical readiness report only. This file is dated context and not the live score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.

# Global Readiness Evidence Report

Date: 2026-03-13  
Objective: Clear strict readiness blockers, convert provisional scoring into evidence-backed status, and synchronize the canonical protocol.

## 1) Release-Gate Commands
Executed and PASS:
- `python backend/manage.py showmigrations`
- `python backend/manage.py migrate --plan`
- `python backend/manage.py check`
- `python scripts/check_idempotency_actions.py` (logic PASS via temp-report fallback because repo report path is locally write-locked)
- `python scripts/check_no_float_mutations.py` (logic PASS via temp-report fallback because repo report path is locally write-locked)
- `python scripts/check_farm_scope_guards.py`
- `python scripts/verification/check_no_bare_exceptions.py`
- `python scripts/verification/detect_zombies.py`
- `python scripts/verification/detect_ghost_triggers.py`
- `python scripts/verification/check_compliance_docs.py`
- `python scripts/verification/check_backup_freshness.py`
- `python scripts/verification/check_restore_drill_evidence.py`
- `python scripts/verification/check_mojibake_frontend.py`
- `python backend/scripts/check_zakat_harvest_triggers.py`
- `python backend/scripts/check_solar_depreciation_logic.py`

Key closure points:
- Django verification commands no longer fail on the local logging handler.
- Production code no longer contains bare `except Exception` in the guarded scan.
- Farm-scope guard validation now passes with a documented global exception for `PermissionTemplateViewSet`.
- Idempotency and float scans now pass logically on the current tree; the only remaining quirk is local write-locking on the repo report artifacts inside `backend/scripts`, mitigated by explicit temp-report evidence.

## 2) Targeted Regression Evidence
Executed and PASS:
- `python backend/manage.py test smart_agri.finance.tests.test_fiscal_lifecycle smart_agri.finance.tests.test_fiscal_year_rollover_idempotency smart_agri.core.tests.test_zakat_policy_v2 smart_agri.core.tests.test_seasonal_settlement smart_agri.core.tests.test_sharecropping_posting_service --keepdb --noinput` (`24/24`)
- `npm --prefix frontend run test -- src/components/daily-log/__tests__/DailyLogResources.test.jsx src/auth/__tests__/modeAccess.test.js --run` (`5/5`)

Covered readiness axes:
- Axis 2: idempotency replay and rejection paths
- Axis 3: fiscal lifecycle transitions
- Axis 9: zakat and solar depreciation
- Axis 13: seasonal settlement
- Axis 15: sharecropping financial and physical modes
- Frontend RTL/mode-access contract smoke

## 3) Runtime Probe Evidence
Executed and PASS:
- `python backend/manage.py shell -c "from smart_agri.core.models.hr import Employee; print(list(Employee.objects.values_list('id','category')[:1]))"`
- `python backend/manage.py shell -c "from smart_agri.core.models.log import IdempotencyRecord; print(list(IdempotencyRecord.objects.values_list('id','response_status')[:1]))"`
- `python backend/manage.py shell -c "from smart_agri.core.models.log import DailyLog; print(list(DailyLog.objects.values_list('id','variance_status')[:1]))"`
- `python backend/manage.py shell -c "from smart_agri.finance.models import FiscalPeriod; print(list(FiscalPeriod.objects.values_list('id','status')[:1]))"`
- `python backend/manage.py shell -c "from smart_agri.core.models import Farm; print(list(Farm.objects.values_list('id','tier')[:1]))"`
- `python backend/manage.py shell -c "from smart_agri.accounts.models import RoleDelegation; print('RoleDelegation table exists:', RoleDelegation.objects.model._meta.db_table)"`

Observed sample outputs confirmed:
- employee categories resolve correctly
- idempotency records are queryable
- daily log variance state is populated
- fiscal periods are readable
- farm tiering is present
- role delegation table exists in the expected schema

## 4) Protocol Sync
Updated successfully:
- Root `AGENTS.md` now uses evidence-gated wording for 18 axes and expanded self-correction commands.
- `agri_guardian` no longer advertises a stale 15-axis constitution or duplicate Axis 11-15 sections.
- `financial_integrity` and `auditor` now enforce evidence-gated scoring expectations.
- Root `AGENTS.md` now contains an explicit `Daily Execution Smart Card Contract`:
  - `CropPlan -> DailyLog -> Activity -> Smart Card -> Control -> Variance -> Ledger`
  - smart card is read-side only
  - this workflow is explicitly non-QR
  - routine tree loss is separated from Axis 18 mass-casualty impairment
- Added `docs/doctrine/DAILY_EXECUTION_SMART_CARD.md` as a canonical doctrine page for this workflow and linked it from `AGENTS.md`.
- `agri_guardian`, `financial_integrity`, and `auditor` now align on the same contract, same non-QR rule, and the same smart-card release evidence.

Residual tooling note:
- Three legacy schema-skill files under `.agent/skills/` remain ACL-locked for the current user on this machine: `schema_guardian/SKILL.md`, `schema_sentinel/SKILL.md`, and `sql_sync/SKILL.md`.
- Root `AGENTS.md` now marks `schema_sentinel` and `sql_sync` as deprecated aliases, which is the canonical in-repo mitigation until those locked files can be edited.
- `docs/doctrine/VERIFICATION_COMMANDS.md` remained locally write-locked during this sync pass, so the canonical smart-card gate is duplicated in `AGENTS.md` and the active skills until the doctrine file can be rewritten cleanly.

## 5) Smart DailyLog Card Release Gate
Executed and PASS:
- `python backend/manage.py test smart_agri.core.tests.test_service_cards smart_agri.core.tests.test_tree_inventory_service smart_agri.core.tests.test_tree_inventory_sync smart_agri.core.tests.test_tree_variance smart_agri.core.tests.test_daily_log_tree_api smart_agri.core.tests.test_tree_census_service --keepdb --noinput` (`16/16`)
- `npm --prefix frontend run test -- src/components/daily-log/__tests__/DailyLogSmartCard.test.jsx src/pages/__tests__/ServiceCards.test.jsx --run` (`3/3`)
- `npm --prefix frontend run build`
- `npx playwright test tests/e2e/daily-log-smart-card.spec.js --project=chromium --config=playwright.config.cjs --output=.pw-results-smart-card` (`3/3`)

Smart-card gate scope:
- DailyLog smart card is now evidence-gated inside the actual daily execution flow, not only on the standalone service-cards dashboard.
- The live Playwright gate proves:
  - seasonal crop context renders the smart card with plan/task/control/variance/ledger data
  - perennial crop context renders the smart card with the same integrated evidence
  - switching the daily-log context updates the smart card in-place
  - both seasonal and perennial daily logs can still be saved successfully after the smart-card assertions

Scoring impact:
- `Smart Cards inside DailyLog`: raised from `94/100` to **`100/100`**
- Reason: the remaining proof gap was closed by a live browser gate on seeded data, plus stable component-level selectors and frontend integration coverage.

## 6) Final Status
- Dual-mode live Playwright matrix executed and PASS:
  - `npx --prefix frontend playwright test frontend/tests/e2e/fixed-assets.spec.js frontend/tests/e2e/fuel-reconciliation.spec.js frontend/tests/e2e/dual-mode-switch.spec.js frontend/tests/e2e/petty-cash.spec.js frontend/tests/e2e/supplier-settlement.spec.js frontend/tests/e2e/contract-operations.spec.js --config=frontend/playwright.config.cjs --project=chromium --workers=1 --output=frontend/.pw-results-live-dual-mode-final` (`6/6`)
- Fuel reconciliation live gate executed and PASS:
  - `npx --prefix frontend playwright test frontend/tests/e2e/fuel-reconciliation.spec.js --config=frontend/playwright.config.cjs --project=chromium --output=frontend/.pw-results-live-fuel` (`1/1`)
- Daily execution smart-card live gate re-executed and PASS:
  - `npx --prefix frontend playwright test frontend/tests/e2e/daily-log-smart-card.spec.js --config=frontend/playwright.config.cjs --project=chromium --workers=1 --output=frontend/.pw-results-live-daily-smart-card` (`3/3`)
- Release-gate commands: PASS
- Runtime probes: PASS
- Targeted regression suite: PASS
- Smart DailyLog card release gate: PASS
- Dual-mode institutional release gates: PASS
- Governance freshness: PASS
- Tenant isolation guard scan: PASS
- Strict readiness status: **100/100 for the project codebase on the current tree, with documented local ACL residuals limited to legacy report/script artifact paths and legacy locked doctrine aliases**
> [!IMPORTANT]
> Historical readiness report only. This file preserves a dated run and does not define the current project score.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.
