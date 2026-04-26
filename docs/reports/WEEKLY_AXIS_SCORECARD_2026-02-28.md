> [!IMPORTANT]
> Historical or scoped report only. This file is dated context and not the live score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.

# WEEKLY AXIS SCORECARD

- REPORT_DATE: `2026-02-28`
- REPORT_SCOPE: `AgriAsset (YECO Edition)`
- AUDITOR: `Codex (Agri-Guardian + Auditor)`
- BASELINE_TARGET: `100/100`

## Overall Score
- TOTAL_SCORE: `100/100`
- STATUS: `PASS`

## Axis Scores
1. Axis 1 Migration/Schema Parity: `10/10` - `showmigrations clean + migrate --plan (No planned operations)`
2. Axis 2 Idempotency V2 & Offline Immunity: `10/10` - `check_idempotency_actions PASS (classes_scanned=89) + replay-safe tests PASS`
3. Axis 3 Fiscal Lifecycle & Period Locking: `10/10` - `FiscalPeriod.status runtime probe PASS + financial workflow E2E PASS`
4. Axis 4 Fund Accounting & Sector Governance: `10/10` - `financial workflow + sales lifecycle E2E PASS`
5. Axis 5 Decimal & Surra Integrity: `10/10` - `check_no_float_mutations PASS + labor estimation API tests PASS`
6. Axis 6 Tenant Isolation & RLS: `10/10` - `runtime probes + RLS-protected API tests PASS`
7. Axis 7 Auditability & Append-Only Chain: `10/10` - `ledger workflows and idempotent mutations validated; no immutable-row mutation findings`
8. Axis 8 Variance & Approval Controls: `10/10` - `Daily Log unit/E2E contracts PASS`
9. Axis 9 Zakat & Solar Compliance: `10/10` - `check_zakat_harvest_triggers PASS + check_solar_depreciation_logic PASS`
10. Axis 10 Farm Tiering & Governance: `10/10` - `Farm.tier + RoleDelegation runtime probes PASS`

## Blocking Findings (If Any)
- None.

## Mandatory Evidence Checklist
- [x] `python backend/manage.py showmigrations`
- [x] `python backend/manage.py migrate --plan`
- [x] `python backend/manage.py check`
- [x] `python scripts/check_no_float_mutations.py`
- [x] `python scripts/check_idempotency_actions.py`
- [x] `python scripts/verification/detect_zombies.py`
- [x] `python scripts/verification/detect_ghost_triggers.py`
- [x] `python backend/scripts/check_zakat_harvest_triggers.py`
- [x] `python backend/scripts/check_solar_depreciation_logic.py`
- [x] `python backend/manage.py test smart_agri.core.tests.test_zakat_policy_v2 --keepdb --noinput`
- [x] `python backend/manage.py test smart_agri.core.tests.test_labor_estimation_api --keepdb --noinput`
- [x] `npm --prefix frontend run test -- src/components/daily-log/__tests__/DailyLogResources.test.jsx --run`
- [x] `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run`
- [x] `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1`
- [x] `npm --prefix frontend run test:e2e -- tests/e2e/financial_workflow.spec.js --workers=1`
- [x] `npm --prefix frontend run test:e2e -- tests/e2e/sales_financial_lifecycle.spec.js --workers=1`
- [x] `npm --prefix frontend run test:e2e -- tests/e2e/finance.spec.js --workers=1`
- [x] `python scripts/verification/check_compliance_docs.py`
- [x] `python scripts/verification/check_backup_freshness.py`
- [x] `python scripts/verification/check_restore_drill_evidence.py`

## Sign-Off
- REVIEWED_BY: `Codex`
- APPROVED_BY: `Pending Maintainer`
- RELEASE_DECISION: `APPROVE`
> [!IMPORTANT]
> Historical weekly scorecard only. This file does not define the live project score.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.
