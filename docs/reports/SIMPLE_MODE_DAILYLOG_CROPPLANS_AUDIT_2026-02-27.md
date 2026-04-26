# Simple Mode Audit: Daily Log History <-> Crop Plans (2026-02-27)

## Scope
- Mode: `strict_erp_mode=false` (Simple Mode only)
- UI focus:
  - `/daily-log-history`
  - `/crop-plans`
  - `/daily-log`
- Governance focus:
  - Daily activity traceability to crop plans
  - Variance/approval behavior in history
  - Simple-vs-Strict route gating consistency

## Implemented Fixes
1. Backend `CropPlanViewSet.variance` contract aligned with frontend needs.
2. Backend `DailyLogViewSet` now supports `status` query filter (`iexact`).
3. Backend `ActivityService` deterministic crop-plan resolver added:
   - prefers exact `farm+crop+location+date`
   - allows unique deterministic fallback at `farm+crop(+date)`
   - rejects ambiguous cases.
4. Frontend `Nav` strict-only visibility fixed for `predictive-variance`.
5. Frontend `DailyLogHistory` approval gate widened to include farm manager/supervisor roles.
6. Frontend `DailyLog` sends linked `crop_plan` when available.
7. E2E stabilized:
   - `all_pages.spec.js` rewritten mode-aware.
   - new `daily-log-history-governance.spec.js` added.
   - `daily-log-seasonal-perennial.spec.js` improved for plan/location selection.

## Verification Commands (Executed)
- `python backend/manage.py check` -> PASS
- `python backend/manage.py migrate --plan` -> PASS
- `python backend/manage.py showmigrations` -> PASS (all applied)
- `python scripts/check_idempotency_actions.py` -> PASS
- `python scripts/check_no_float_mutations.py` -> PASS
- `python scripts/check_farm_scope_guards.py` -> PASS
- `python scripts/check_fiscal_period_gates.py` -> PASS
- `python scripts/verification/detect_zombies.py` -> PASS
- `python scripts/verification/detect_ghost_triggers.py` -> PASS
- `python backend/scripts/check_zakat_harvest_triggers.py` -> PASS
- `python backend/scripts/check_solar_depreciation_logic.py` -> PASS
- `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/all_pages.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log-seasonal-perennial.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/simple_mode_document_cycle.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log-history-governance.spec.js --workers=1` -> PASS

## Findings Closed
- `HIGH` Crop-plan variance payload mismatch closed.
- `HIGH` Traceability gap (`activity.crop_plan`) closed for normal flow.
- `MEDIUM` Daily-log status filter gap closed.
- `MEDIUM` Simple-mode nav/route mismatch closed.
- `MEDIUM` Approval UI role gate too narrow closed.
- `LOW` Old page-smoke E2E false signals closed.

## Residual Risks
1. Resolver fallback (`farm+crop(+date)` when location-match missing) is deterministic but should be reviewed periodically to ensure no hidden location misrouting when many active plans coexist.
2. Legacy Arabic strings/encodings in some files should be normalized in a dedicated localization cleanup pass.

## Strict Score (In-Scope)
- **97/100**
- Rationale:
  - + Strong alignment on Simple Mode route contract and governance flow.
  - + Traceability and variance controls now test-backed.
  - - 3 points reserved for residual ambiguity risk in fallback selection under highly dense plan configurations.

## Decision
- **GO (Simple Mode in-scope)**
- No blocking regression found in the audited scope.
