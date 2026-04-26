# AgriAsset V21 System Overview

> Reference class: public system overview.
> This file is not a higher-order canonical source than `PRD V21`, `AGENTS.md`, doctrine, or the
> latest canonical evidence under `docs/evidence/closure/latest/`.

This page gives a current high-level map of the platform for onboarding and operator orientation.

## 1. Platform shape
- **Backend**: Django + DRF with service-layer orchestration, mode-aware governance, append-only audit traces, and evidence-gated verification.
- **Frontend**: React + Vite with Arabic RTL-first surfaces, offline-capable daily execution, and mode-aware operational dashboards.
- **Database**: PostgreSQL only. SQLite is banned for governed validation, release gates, and production.
- **Operating model**: `SIMPLE` remains a technical agricultural control surface; `STRICT` exposes the governed ERP controls over the same truth chain.

## 2. Core truth chain
`CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`

- `CropPlan` is the planning source of truth.
- `Activity` is the operational source of truth.
- `smart_card_stack` is read-side only in both modes.
- Costing and posting remain backend-governed.

## 3. API path policy
- Infrastructure endpoints live under `/api/`
  - `/api/health/`
  - `/api/health/live/`
  - `/api/health/ready/`
  - `/api/auth/token/`
  - `/api/auth/refresh/`
  - `/api/schema/`
  - `/api/docs/`
- Business routers live under `/api/v1/`
  - farms, locations, crops, plans, daily logs, activities
  - reports, smart-card consumers, tree inventory, custody, offline replay
  - finance and approvals

## 4. High-value domains
- **Daily execution**: task-driven `DailyLog` with stack-first rendering and backend-only costing.
- **Inventory and custody**: governed stock ledger plus supervisor custody transfer/acceptance/return flows.
- **Biological assets**: tree inventory, cohort integrity, and variance-aware operational corrections.
- **Finance and approvals**: fiscal lifecycle, fund accounting, petty cash, supplier settlement, sector approval chain, and forensic stage events.
- **Reports**: conservative direct reporting plus async export/report jobs over the same backend truth.

## 5. Offline and replay
- Offline field workflows use IndexedDB-backed stores.
- Transactional daily execution uses Dexie-backed queues.
- Daily execution replay is atomic for the `DailyLog` envelope; it is not a split `log -> activity` mutation path.
- Supervisor custody actions use their own governed queue rather than a generic mutation queue.
- Failures record retry metadata and dead-letter state rather than silently dropping intent.

## 6. Reporting contract
- `GET /api/v1/advanced-report/` without explicit `section_scope` is a conservative compatibility path that returns a usable `summary + details` payload.
- Explicit `section_scope` activates sectional optimization only when the client sends it intentionally.
- `include_tree_inventory` remains valid in both conservative and sectional loading.
- Public examples should follow `farm|farm_id`, `location|location_id`, and `season|season_id` support.

## 7. Quickstart
- Backend: `python backend/manage.py migrate`, then `python backend/manage.py runserver`
- Frontend: `npm --prefix frontend run dev`
- Canonical checks:
  - `python scripts/verification/check_compliance_docs.py`
  - `python backend/manage.py verify_static_v21`
  - `python backend/manage.py verify_release_gate_v21`
  - `python backend/manage.py verify_axis_complete_v21`

## 8. Where to read next
- Product baseline: `docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md`
- Execution protocol: `AGENTS.md`
- Dual-mode doctrine: `docs/doctrine/HYBRID_MODE_V2.md`
- Operational cycles: `docs/doctrine/DUAL_MODE_OPERATIONAL_CYCLES.md`
- Smart-card doctrine: `docs/doctrine/DAILY_EXECUTION_SMART_CARD.md`
- Public API guide: `docs/API_REFERENCE.md`
