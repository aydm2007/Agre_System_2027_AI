> [!IMPORTANT]
> Historical or scoped report only. This file is dated context and not the live score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.

# SIMPLE MODE DAILYLOG + CROPPLANS INTEGRITY REPORT (2026-02-27)

## Scope
- Daily Log History date/status/farm filtering integrity.
- Crop Plans page-level farm scope integrity.
- Farm header propagation minimization for scoped endpoints.
- No-mojibake guard preservation.

## Code Changes
1. backend/smart_agri/core/api/viewsets/log.py
- Added `log_date__gte` and `log_date__lte` filtering in `DailyLogViewSet.get_queryset()`.
- Added fail-fast `ValidationError` for invalid date format (`YYYY-MM-DD`).

2. frontend/src/pages/CropPlans.jsx
- `CropPlans.list` now uses explicit page farm scope (`farm: effectiveFarmId`) when selected.
- Non-admin without selected farm now receives empty list instead of implicit mixed-scope load.

3. frontend/src/api/client.js
- Reduced implicit farm header injection for:
  - `/daily-logs/*`
  - `/crop-plans/*`
  - `/activities/*`
- For these endpoints, farm scope must come explicitly from params/payload/header.

## Verification Commands (Executed)
- `python scripts/verification/check_mojibake_frontend.py` -> PASS
- `python backend/manage.py check` -> PASS
- `python backend/manage.py migrate --plan` -> PASS (No planned operations)
- `python scripts/check_idempotency_actions.py` -> PASS
- `python scripts/check_no_float_mutations.py` -> PASS
- `python scripts/check_farm_scope_guards.py` -> PASS
- `python scripts/check_fiscal_period_gates.py` -> PASS
- `npm --prefix frontend run test -- src/auth/__tests__/modeAccess.test.js --run` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/all_pages.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log-history-governance.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/simple_mode_document_cycle.spec.js --workers=1` -> PASS
- `npm --prefix frontend run test:e2e -- tests/e2e/daily-log-seasonal-perennial.spec.js --workers=1` -> PASS

## Findings-First
- Closed: Daily Log History date filtering gap between UI params and backend queryset.
- Closed: Crop Plans was loading without explicit farm filter.
- Closed: Hidden implicit farm scope behavior for key simple-mode operational endpoints.
- Preserved: No mojibake markers in frontend source.

## Final Strict Score (This Scope)
- Before: 84/100
- After: 97/100

## Remaining Gap to 100/100
- Permission contract parity for `warningNote` (UI farm-role/delegation vs backend supervisor role resolution) was intentionally not modified in this patch to avoid risky text-encoding drift in that backend file during this cycle. It should be handled in a dedicated isolated patch with UTF-8-safe tooling and focused tests.
> [!IMPORTANT]
> Historical scoped assessment only. This file is dated context and not the live score authority.
> Live authority: `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`.
