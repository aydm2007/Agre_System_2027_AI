> [!IMPORTANT]
> Historical readiness report only. This file is dated context and not the live score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.

# Global Readiness Evidence Report

Date: 2026-03-03
Objective: Monthly evidence refresh — maintain 100/100 compliance axes and close evidence staleness gap.

## 1) Functional Gate Evidence (AGENTS baseline)
Executed and PASS:
- `python backend/manage.py showmigrations`
- `python backend/manage.py migrate --plan`
- `python backend/manage.py check`
- `python scripts/check_no_float_mutations.py`
- `python scripts/check_idempotency_actions.py`
- `python scripts/check_farm_scope_guards.py`
- `python scripts/check_fiscal_period_gates.py`
- `python scripts/verification/detect_zombies.py`
- `python scripts/verification/detect_ghost_triggers.py`
- `python backend/scripts/check_zakat_harvest_triggers.py`
- `python backend/scripts/check_solar_depreciation_logic.py`
- `python backend/manage.py test smart_agri.core.tests.test_zakat_policy_v2 --keepdb --noinput`
- `python backend/manage.py test smart_agri.core.tests.test_financial_governance --keepdb`

## 2) E2E Contract Evidence (Windows sequential)
Executed and PASS (sequential, `--workers=1`):
- `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run`
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1`
- `npm --prefix frontend run test:e2e -- tests/e2e/financial_workflow.spec.js --workers=1`
- `npm --prefix frontend run test:e2e -- tests/e2e/sales_financial_lifecycle.spec.js --workers=1`
- `npm --prefix frontend run test:e2e -- tests/e2e/finance.spec.js --workers=1`

Note: Windows host — `verify_release_gate.sh` equivalent commands executed directly.

## 3) Non-Functional Governance Deliverables
Created and current:
- `docs/compliance/ISMS_SCOPE_AND_RISK_REGISTER.md`
- `docs/compliance/SECURITY_CONTROLS_MATRIX.md`
- `docs/compliance/DR_BCP_RUNBOOK.md`
- `docs/compliance/DATA_GOVERNANCE_STANDARD.md`
- `docs/compliance/RELEASE_GOVERNANCE_STANDARD.md`
- `docs/reports/GLOBAL_BASELINE_GAP_REGISTER.md`
- `docs/reports/DR_DRILL_2026-03-02.md` (fresh — within 45-day window)

## 4) Policy-as-Code Evidence
Executed and PASS:
- `python scripts/verification/check_compliance_docs.py`
- `python scripts/verification/check_backup_freshness.py`
- `python scripts/verification/check_restore_drill_evidence.py`

CI enforcement active:
- `.github/workflows/nonfunctional-compliance-gate.yml`
- `.github/workflows/ci.yml` (nonfunctional job)
- `.github/workflows/backend-postgres-tests.yml` (nonfunctional step)

## 5) Agent/Skill Protocol Alignment
Current and verified:
- `AGENTS.md` — 11 Axes, Global Readiness controls, blocking rules
- `.agent/skills/agri_guardian/SKILL.md` — non-functional evidence requirements
- `.agent/skills/financial_integrity/SKILL.md` — governance evidence linkage
- `.agent/skills/schema_sentinel/SKILL_NEW.md` — DR schema/restore evidence protocol

## 6) Runtime Probes (Fail-Fast)
All runtime probes successful:
- `Employee.category` column: accessible
- `IdempotencyRecord.response_status/body`: accessible
- `DailyLog.variance_status`: accessible
- `FiscalPeriod.status`: accessible
- `Farm.tier`: accessible
- `RoleDelegation` table: exists

## 7) Final Status
- Functional controls: PASS
- Non-functional governance controls: PASS
- Evidence traceability: PASS
- DR Drill freshness: PASS (2026-03-02, within 45-day window)
- Repo+Ops readiness closure: **100/100**

## 8) External Gate Disclaimer
Formal third-party certification issuance (e.g., ISO/SOC attestation letter) remains an organization-level external process outside repository scope.

## 9) Evidence Refresh Schedule
- Next evidence refresh: 2026-04-03 (monthly cadence)
- Next DR drill: 2026-04-02 (monthly cadence)
- Evidence staleness threshold: 45 days from this report date
> [!IMPORTANT]
> Historical readiness report only. This file preserves a dated run and does not define the current project score.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.
