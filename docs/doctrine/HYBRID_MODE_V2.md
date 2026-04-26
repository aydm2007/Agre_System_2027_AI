# Hybrid Mode Doctrine v2

This is the current readable dual-mode reference when legacy doctrine files are outdated or locked.

## Primary Control Source

- `FarmSettings` is the primary source of truth for mode and policy behavior per farm.
- `SystemSettings.strict_erp_mode` may remain as a legacy global override or bootstrap signal, but new behavior must be modeled through `FarmSettings`.
- `system-mode` exposes effective mode and policy snapshot to the frontend.

## Shared Truth

Both modes use the same operational and financial truth:

- `CropPlan`
- `DailyLog`
- `Activity`
- `Variance`
- `AuditLog`
- `FinancialLedger`

Mode differences must come from policy, visibility, and action exposure. They must not come from duplicate posting engines or duplicate transactional models.

## SIMPLE

`SIMPLE` is a technical agricultural control system.

It exposes:

- plans
- materials
- tasks
- daily execution
- smart cards
- variance and alert posture
- agronomic and control reports
- cost summaries according to policy

It reduces or hides:

- raw ledger authoring
- treasury authoring for non-finance users
- full supplier settlement controls
- full contract settlement economics
- full fixed-asset capitalization controls when `fixed_asset_mode=full_capitalization`

It still preserves shadow accounting, idempotency, farm isolation, auditability, and approval continuity.
Mode-aware dashboards for contract operations, fixed assets, and fuel reconciliation remain readable in `SIMPLE`, but governed mutation actions stay blocked in backend policy and audited when breached.
The `/finance` hub may expose append-only shadow daily journal entries in `SIMPLE` as a read-only visibility surface over the same `FinancialLedger` truth. This does not reopen ledger authoring, treasury mutation, or governed settlement controls.
Legacy flags such as `show_finance_in_simple`, `show_stock_in_simple`, and `show_employees_in_simple` are `compatibility-only` and `display-only`. They are `not authoring authority` for route registration, backend mutation permission, or ERP authoring in `SIMPLE`.
For supervisor-led daily execution, `SIMPLE` may expose custody posture and accepted-balance visibility only. Main warehouse authoring, issue approval, and custody reconciliation remain governed workflows outside the field execution surface.

## STRICT

`STRICT` exposes full ERP controls over the same truth.

It includes everything in `SIMPLE`, plus:

- treasury visibility
- receipts and deposit trace
- petty cash settlement
- supplier settlement review, approval, payment, and reconciliation
- contract operations with settlement trace
- fixed-asset dashboards plus governed capitalization and disposal evidence
- fuel reconciliation dashboards plus governed posting and seeded runtime evidence
- mode-aware integration/readiness defaults should enable strict farm scope headers and a non-logging integration publisher outside local development

## Policy Fields

The current system behavior relies on:

- `mode` - Checked centrally via `mode_policy_service.is_finance_authoring_allowed(farm)`
- `variance_behavior`
- `cost_visibility` - Controls SIMPLE mode dashboard burn-rate leaks mapping (M3.6 leakage prevention)
- `approval_profile`
- `contract_mode`
- `treasury_visibility`
- `fixed_asset_mode`
- fuel dashboards also consume `cost_visibility`, `variance_behavior`, and `treasury_visibility`

## Security and System Traces
- **Route Breach Middleware**: Unauthorized access to strict API endpoints generates a `ROUTE_BREACH_SIMPLE_MODE` JSON payload alongside an `AuditLog` entry tracing the actor.
- **Shadow Accounting**: Activity workflows in `SIMPLE` mode successfully construct continuous shadow `FinancialLedger` lines silently beneath the explicit dashboard view.
- **Custody Handshake**: Inventory transferred from the main warehouse to field execution must pass through `issued_pending_acceptance -> accepted` before `DailyLog` consumption is permitted. Rejections and returns reverse through the same service layer; no parallel sub-inventory ledger is allowed.
- **Offline Atomic Replay**: `SIMPLE` operational replay may queue append-only technical envelopes offline, but server state remains authoritative and out-of-order replays must enter `SyncConflictDLQ` rather than mutating stock silently.

## Reference Integrity

- A workflow is not hybrid-complete if it exists in code but not in doctrine or skills.
- Historical doctrine snapshots may preserve older wording, but the active reference layer must reflect the current governed evidence state.
- Traceability for dual-mode enforcement must remain explicit:
  - code anchor: `backend/smart_agri/core/permissions.py`, `backend/smart_agri/core/middleware/route_breach_middleware.py`
  - test anchor: `backend/smart_agri/core/tests/test_v21_simple_mode_display_flags.py`
  - gate anchor: `python backend/manage.py verify_release_gate_v21`, `python backend/manage.py verify_axis_complete_v21`
  - evidence anchor: latest summaries under `docs/evidence/closure/latest/`
