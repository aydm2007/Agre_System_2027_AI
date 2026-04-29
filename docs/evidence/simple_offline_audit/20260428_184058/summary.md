# AgriAsset SIMPLE / Offline Audit

Generated: 2026-04-28 18:40 local time

## Verdict

Strict score: **96 / 100**

Recommendation: **Ready for governed demo operation**. The Offline DailyLog path, SIMPLE route posture, frontend build, backend replay tests, Playwright SIMPLE journeys, and canonical V21 gate all passed. This is not scored 100 because the frontend lint still reports two non-blocking hook dependency warnings and the production build still emits a large chunk warning; both are technical debt, not runtime blockers.

## Demo Data

Command:

```powershell
python backend/manage.py seed_simple_offline_demo_data --reset-demo --with-offline-fixtures
```

Result: PASS

Created/updated idempotent demo data:

- Farm: `Simple Offline Demo Farm`
- Farm slug: `simple-offline-demo-farm`
- Mode: `SIMPLE`
- User: `simple_offline_demo`
- Password: `DemoOffline2026!`
- Crop: mango demo crop
- Location: demo location 1
- Crop plan, task `الكل`, all operational smart cards enabled
- DailyLog + Activity + service coverage + material issue
- Offline fixtures: `pending`, `syncing stale`, `dead_letter retryable`, `idempotency mismatch recovery`
- Server evidence fixtures: 4 `SyncRecord`, 1 `SyncConflictDLQ`, 1 `OfflineSyncQuarantine`

The same seed command passed twice in the test database through `test_seed_simple_offline_demo_data_command`, proving repeatability.

## Fixes Applied

- Added `seed_simple_offline_demo_data` management command for repeatable SIMPLE/offline demo data.
- Added backend seed idempotency test coverage.
- Restored soft-deleted demo DLQ/quarantine rows on reseed by resetting `deleted_at=None` and `is_active=True`.
- Hardened SIMPLE route guard coverage by explicitly guarding `/finance/ledger` with `canRegisterFinancialRoutes`.
- Updated SIMPLE Playwright expectations so `/finance` remains posture/read-only while `/finance/ledger` is blocked in SIMPLE.

## Verification Commands

| Area | Command | Result |
| --- | --- | --- |
| Demo seed | `python backend/manage.py seed_simple_offline_demo_data --reset-demo --with-offline-fixtures` | PASS |
| E2E auth seed | `python backend/manage.py prepare_e2e_auth_v21` | PASS |
| Backend SIMPLE/offline | `python backend/manage.py test smart_agri.core.tests.test_offline_daily_log_replay smart_agri.core.tests.test_simple_strict_separation smart_agri.core.tests.test_simple_no_finance_leak smart_agri.core.tests.test_shadow_ledger_readonly smart_agri.core.tests.test_seed_simple_offline_demo_data_command --keepdb --noinput` | PASS, 20 tests |
| Backend service/fuel | `python backend/manage.py test smart_agri.core.tests.test_service_cards smart_agri.core.tests.test_fuel_reconciliation_dashboard_api --keepdb --noinput` | PASS, 13 tests |
| Frontend targeted | `npm --prefix frontend run test -- --run src/api/__tests__/offlineQueueUtils.test.js src/offline/__tests__/OfflineQueueProvider.test.jsx src/components/offline/__tests__/OfflineQueuePanel.test.jsx src/hooks/__tests__/useDailyLogForm.test.js src/components/daily-log/__tests__/DailyLogSmartCard.test.jsx src/__tests__/appRouteGuards.test.js` | PASS, 30 tests |
| Route guard retest | `npm --prefix frontend run test -- --run src/__tests__/appRouteGuards.test.js` | PASS |
| Lint | `npm --prefix frontend run lint` | PASS with 2 warnings |
| Build | `npm --prefix frontend run build` | PASS with chunk-size warning |
| Playwright SIMPLE/offline | `npx --prefix frontend playwright test frontend/tests/e2e/simple_mode_isolation.spec.js frontend/tests/e2e/simple-mode-governed-cycles-ar.spec.js frontend/tests/e2e/daily-log-smart-card.spec.js frontend/tests/e2e/fuel-reconciliation.spec.js frontend/tests/e2e/dual-mode-switch.spec.js --project=chromium --config=frontend/playwright.config.js --workers=1 --reporter=line` | PASS, 8 tests |
| Canonical gate | `python backend/manage.py verify_axis_complete_v21` | PASS |

Canonical gate output:

```text
PASS: axis_1 Schema Parity
PASS: axis_2 Idempotency V2
PASS: axis_3 Fiscal Lifecycle
PASS: axis_4 Fund Accounting
PASS: axis_5 Decimal and Surra
PASS: axis_6 Tenant Isolation
PASS: axis_7 Auditability
PASS: axis_8 Variance and BOM
PASS: axis_9 Sovereign and Zakat
PASS: axis_10 Farm Tiering
PASS: axis_11 Biological Assets
PASS: axis_12 Harvest Compliance
PASS: axis_13 Seasonal Settlement
PASS: axis_14 Schedule Variance
PASS: axis_15 Sharecropping
PASS: axis_16 Single-Crop Costing
PASS: axis_17 Petty Cash Settlement
PASS: axis_18 Mass Exterminations
overall_status=PASS
axis_overall_status=PASS
```

Canonical evidence path:

`docs/evidence/closure/20260428_183244/verify_axis_complete_v21`

Latest canonical summary:

`docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`

## Scoring

| Rubric | Score | Notes |
| --- | ---: | --- |
| Offline sync readiness | 25 / 25 | DailyLog replay, mismatch recovery, stale syncing refresh, auto-sync provider, and queue panel tests passed. |
| SIMPLE/STRICT boundary safety | 20 / 20 | Backend authoring blocks, frontend ModeGuard route scan, and SIMPLE Playwright isolation passed. |
| Frontend runtime/build/UI safety | 18 / 20 | Vitest, lint, build, and Playwright passed; two hook warnings and chunk-size warning remain. |
| Backend API/domain integrity | 19 / 20 | Targeted backend suites and canonical gate passed; non-fatal runtime warnings remain in existing fixture-heavy tests. |
| Evidence, seed repeatability, report trust | 14 / 15 | Demo seed is repeatable in Dev/Test DB and report is linked to canonical gate; score held below full until lint/build warnings are retired. |

Total: **96 / 100**

## Residual Issues

- `frontend/src/contexts/SettingsContext.jsx` has an existing `react-hooks/exhaustive-deps` warning for `isAuthenticated`.
- `frontend/src/pages/settings/TeamBuilderTab.jsx` has an existing `react-hooks/exhaustive-deps` warning for `page`.
- Vite production build emits a chunk-size warning for large bundles.
- The canonical gate is PASS, but future production certification should still include a real browser manual spot-check against the deployed host after these code changes are deployed.

