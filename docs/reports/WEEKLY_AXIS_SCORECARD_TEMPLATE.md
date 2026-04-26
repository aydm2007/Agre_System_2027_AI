> [!IMPORTANT]
> Template only. This file is a scoring worksheet and not a live readiness claim.
> Live authority for project-wide status remains `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.

# WEEKLY AXIS SCORECARD

- REPORT_DATE: `<YYYY-MM-DD>`
- REPORT_SCOPE: `AgriAsset (YECO Edition)`
- AUDITOR: `<name>`
- BASELINE_TARGET_IF_PASS_PASS: `100/100`

## Overall Score
- TOTAL_SCORE: `<0-100>`
- STATUS: `PASS|BLOCK`

## Axis Scores
1. Axis 1 Migration/Schema Parity: `<score>/10` - `<evidence>`
2. Axis 2 Idempotency V2 & Offline Immunity: `<score>/10` - `<evidence>`
3. Axis 3 Fiscal Lifecycle & Period Locking: `<score>/10` - `<evidence>`
4. Axis 4 Fund Accounting & Sector Governance: `<score>/10` - `<evidence>`
5. Axis 5 Decimal & Surra Integrity: `<score>/10` - `<evidence>`
6. Axis 6 Tenant Isolation & RLS: `<score>/10` - `<evidence>`
7. Axis 7 Auditability & Append-Only Chain: `<score>/10` - `<evidence>`
8. Axis 8 Variance & Approval Controls: `<score>/10` - `<evidence>`
9. Axis 9 Zakat & Solar Compliance: `<score>/10` - `<evidence>`
10. Axis 10 Farm Tiering & Governance: `<score>/10` - `<evidence>`

## Blocking Findings (If Any)
- Severity: `CRITICAL|HIGH|MEDIUM|LOW`
- File: `<path>`
- Violation: `<description>`
- Yemen Context Impact: `<manual mode | surra | decimal | weak network>`
- Remediation Snippet:
```python
# production-ready patch snippet
```

## Mandatory Evidence Checklist
- [ ] `python backend/manage.py showmigrations`
- [ ] `python backend/manage.py migrate --plan`
- [ ] `python backend/manage.py check`
- [ ] `python scripts/check_no_float_mutations.py`
- [ ] `python scripts/check_idempotency_actions.py`
- [ ] `python scripts/verification/detect_zombies.py`
- [ ] `python scripts/verification/detect_ghost_triggers.py`
- [ ] `python backend/scripts/check_zakat_harvest_triggers.py`
- [ ] `python backend/scripts/check_solar_depreciation_logic.py`
- [ ] `python backend/manage.py test smart_agri.core.tests.test_zakat_policy_v2 --keepdb --noinput`
- [ ] `python backend/manage.py test smart_agri.core.tests.test_labor_estimation_api --keepdb --noinput`
- [ ] `npm --prefix frontend run test -- src/components/daily-log/__tests__/DailyLogResources.test.jsx --run`
- [ ] `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run`
- [ ] `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1`
- [ ] `npm --prefix frontend run test:e2e -- tests/e2e/financial_workflow.spec.js --workers=1`
- [ ] `npm --prefix frontend run test:e2e -- tests/e2e/sales_financial_lifecycle.spec.js --workers=1`
- [ ] `npm --prefix frontend run test:e2e -- tests/e2e/finance.spec.js --workers=1`
- [ ] `python scripts/verification/check_compliance_docs.py`
- [ ] `python scripts/verification/check_backup_freshness.py`
- [ ] `python scripts/verification/check_restore_drill_evidence.py`

## Sign-Off
- REVIEWED_BY: `<name>`
- APPROVED_BY: `<name>`
- RELEASE_DECISION: `APPROVE|BLOCK`
