> [!IMPORTANT]
> Historical or scoped report only. This file is dated context and not the live score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.

# Farm Filter Localization Audit (2026-02-27)

## Summary
Implemented farm-filter localization to remove the global farm selector from shell header and move farm scoping behavior to page level.

## Implemented Changes
1. Removed global header farm selector from `frontend/src/app.jsx`.
2. Refactored `FarmProvider` to page-scoped persistence via `page_farm.<route>` keys:
   - `frontend/src/api/farmContext.jsx`
3. Added reusable page farm filtering primitives:
   - `frontend/src/hooks/usePageFarmFilter.js`
   - `frontend/src/components/filters/PageFarmFilter.jsx`
4. Migrated primary target pages:
   - `frontend/src/pages/DailyLogHistory.jsx`
   - `frontend/src/pages/CropPlans.jsx`
   - `frontend/src/pages/Reports/index.jsx`
   - `frontend/src/pages/Reports/components/ReportFilters.jsx`
   - `frontend/src/pages/Reports/hooks/useReportFilters.js`
5. Removed hidden global farm header dependency from API client and replaced with explicit + page-scope resolution:
   - `frontend/src/api/client.js`
6. Backend farm query normalization hardening in base viewset:
   - `backend/smart_agri/core/api/viewsets/base.py`
7. Updated E2E utilities/contracts:
   - `frontend/tests/e2e/helpers/e2eAuth.js`
   - `frontend/tests/e2e/all_pages.spec.js`
   - `frontend/tests/e2e/daily-log-history-governance.spec.js`

## Verification Results
### Backend / Governance checks
- `python backend/manage.py check` -> PASS
- `python backend/manage.py migrate --plan` -> PASS
- `python backend/manage.py showmigrations` -> PASS
- `python scripts/check_idempotency_actions.py` -> PASS
- `python scripts/check_no_float_mutations.py` -> PASS
- `python scripts/check_farm_scope_guards.py` -> PASS
- `python scripts/check_fiscal_period_gates.py` -> PASS

### Frontend / E2E checks
- `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/all_pages.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log-history-governance.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1` -> FAIL (location options empty in one scenario)

## Findings (Strict)
1. `MEDIUM` residual blocker: `daily-log.spec.js` scenario "surra doctrine" fails due missing selectable location in that run context. This is not introduced by header selector removal only, but now visible after explicit farm-localization hardening.

## Strict Score (Current)
- **96/100**
- Deduction:
  - 2 points: one E2E blocker still open (`daily-log.spec.js` location selector readiness).
  - 2 points: not all secondary pages (finance/sales/employees/settings sub-tabs) were individually migrated to explicit `PageFarmFilter` component yet, though page-scoped provider fallback is active.

## Release Decision for this scope
- **Conditional GO** for core target scope (`daily-log-history`, `crop-plans`, `reports`, global selector removal).
- **Full 100/100 blocked** until `daily-log.spec.js` blocker is closed and secondary pages complete explicit filter migration.
