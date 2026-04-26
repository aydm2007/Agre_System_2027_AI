# Baseline - Farm Filter Migration (2026-02-27)

## Scope
- Remove global farm selector from app shell
- Move farm selection to page-local filters
- Keep AGENTS no-regression guarantees

## Initial observations
- Global selector rendered in `frontend/src/app.jsx` via `FarmSelector`.
- Farm selection storage conflict existed:
  - `selected_farm_id` (FarmProvider)
  - `agri-selected-farm` (API header propagation)
- Multiple pages consume `useFarmContext().selectedFarmId`.

## Risk hotspots
1. Hidden global farm scope in API request headers (`X-Farm-ID`) could leak implicit behavior.
2. Existing pages without visible farm filter rely on context default.
3. E2E helper expected global selector test id `farm-selector-button`.

## Baseline checks
- `python backend/manage.py check` : PASS
- `python backend/manage.py showmigrations` : PASS (all applied)
- AGENTS checks were green before migration pass.
