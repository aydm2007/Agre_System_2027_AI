> [!IMPORTANT]
> Historical readiness report only. This file is dated context and not the live score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.

# Global Readiness Evidence Report

Date: 2026-02-27
Objective: Close the non-functional governance gap (9 points) and establish audit-grade Repo+Ops evidence.

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

## 2) E2E Contract Evidence (Windows sequential)
Executed and PASS (sequential, `--workers=1`):
- `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run`
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1`
- `npm --prefix frontend run test:e2e -- tests/e2e/financial_workflow.spec.js --workers=1`
- `npm --prefix frontend run test:e2e -- tests/e2e/sales_financial_lifecycle.spec.js --workers=1`
- `npm --prefix frontend run test:e2e -- tests/e2e/finance.spec.js --workers=1`

Note: `bash scripts/verify_release_gate.sh` is not available on this Windows host (no WSL distro installed), so equivalent commands were executed directly and recorded above.

## 3) Non-Functional Governance Deliverables
Created and versioned:
- `docs/compliance/ISMS_SCOPE_AND_RISK_REGISTER.md`
- `docs/compliance/SECURITY_CONTROLS_MATRIX.md`
- `docs/compliance/DR_BCP_RUNBOOK.md`
- `docs/compliance/DATA_GOVERNANCE_STANDARD.md`
- `docs/compliance/RELEASE_GOVERNANCE_STANDARD.md`
- `docs/reports/GLOBAL_BASELINE_GAP_REGISTER.md`
- `docs/reports/DR_DRILL_2026-02-27.md`

## 4) Policy-as-Code Evidence
Executed and PASS:
- `python scripts/verification/check_compliance_docs.py`
- `python scripts/verification/check_backup_freshness.py`
- `python scripts/verification/check_restore_drill_evidence.py`

CI enforcement added:
- `.github/workflows/nonfunctional-compliance-gate.yml`
- `.github/workflows/ci.yml` (nonfunctional job)
- `.github/workflows/backend-postgres-tests.yml` (nonfunctional step)

## 5) Agent/Skill Protocol Alignment
Updated:
- `AGENTS.md` with Global Readiness Non-Functional Controls and blocking rules.
- `.agent/skills/agri_guardian/SKILL.md` non-functional evidence requirements.
- `.agent/skills/financial_integrity/SKILL.md` governance evidence linkage.
- `.agent/skills/schema_sentinel/SKILL_NEW.md` DR schema/restore evidence protocol.

## 6) Final Status
- Functional controls: PASS.
- Non-functional governance controls: PASS.
- Evidence traceability: PASS.
- Repo+Ops readiness closure: **100/100**.

## 7) External Gate Disclaimer
Formal third-party certification issuance (e.g., ISO/SOC attestation letter) remains an organization-level external process outside repository scope.

## 8) Addendum: Immediate Closure Run (2026-02-27)
Execution objective: close residual gap from `94/100` to `100/100` using verification-only run (no code/schema changes).

Preflight:
- `cmd /c start_dev_stack.bat check` -> PASS
- `http://127.0.0.1:8000/api/health/` -> `200`

Phase 2 (Core/Sovereign/Schema checks):
- `python scripts/verification/detect_zombies.py` -> PASS
- `python scripts/verification/detect_ghost_triggers.py` -> PASS
- `python backend/scripts/check_zakat_harvest_triggers.py` -> PASS
- `python backend/scripts/check_solar_depreciation_logic.py` -> PASS

Phase 3 (Financial E2E, Windows sequential):
- `npm --prefix frontend run test:e2e -- tests/e2e/financial_workflow.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/sales_financial_lifecycle.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/finance.spec.js --workers=1` -> PASS

Phase 4 (Minimum regression pack):
- `python backend/manage.py check` -> PASS
- `python backend/manage.py migrate --plan` -> PASS
- `python scripts/check_idempotency_actions.py` -> PASS
- `python scripts/check_no_float_mutations.py` -> PASS
- `python scripts/check_farm_scope_guards.py` -> PASS
- `python scripts/check_fiscal_period_gates.py` -> PASS

Failure handling:
- No blocker failures.
- No silent skip.
- No rerun required for failed suites.

Decision:
- Final strict score for this closure run: **100/100**.
- Release status: **GO** (within repository + ops verification scope).
> [!IMPORTANT]
> Historical readiness report only. This file preserves a dated run and does not define the current project score.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.
