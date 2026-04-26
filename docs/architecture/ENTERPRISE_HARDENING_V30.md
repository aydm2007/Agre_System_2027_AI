# Enterprise Hardening V30

> Reference class: architecture note.
> This file explains implementation direction and hardening outcomes. It does not outrank `PRD`,
> `AGENTS.md`, doctrine, or latest canonical closure evidence.

This pass continues the path toward a cleaner enterprise platform by targeting reporting modularity and API surface decomposition.

## Changes
- Extracted advanced-report request parsing and farm access resolution into `backend/smart_agri/core/api/reporting_support.py`.
- Centralized advanced-report queryset construction and recent-log payload building into helper functions.
- Reduced orchestration pressure inside `backend/smart_agri/core/api/reporting.py` and made the request contract easier to test.
- Extracted reporting clients from `frontend/src/api/client.js` into `frontend/src/api/reportingClient.js`.
- Finalized the reporting contract as a conservative public API:
  - direct `GET /api/v1/advanced-report/` without explicit `section_scope` returns a usable payload
    with `summary + details`
  - explicit `section_scope` enables sectional optimization only when requested
  - `buildAdvancedReportParams()` stays compatibility-first
  - `buildAdvancedReportParamsWithSections()` remains the async sectional path
- Preserved farm-scoped details and tree-aware filters across both conservative and sectional
  loading paths.
- Hardened Playwright browser startup by loading PostgreSQL environment and running migrations
  before Django `runserver`.

## Enterprise value
- clearer API boundaries
- lower maintenance risk in reporting endpoints
- smaller frontend gateway file
- easier future migration toward typed/reporting domain clients
- deterministic browser proofs that do not depend on stale developer-local schema state
