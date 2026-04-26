# Dual-Mode Operational Cycles

This doctrine defines how implemented and planned workflows behave across `SIMPLE` and `STRICT` modes.

## Core Rule

- `FarmSettings` is the primary source of policy behavior per farm.
- `SIMPLE` reduces ERP clutter but does not reduce backend truth.
- `STRICT` exposes fuller finance, treasury, settlement, and reconciliation controls over the same truth.
- Smart cards are read-side only in both modes.
- `/daily-log/harvest` is a frontend launch alias only. It must route the user into the canonical
  `DailyLog` workflow with harvest-oriented context, not into a second write path.
- `/simple-hub` is a frontend orchestration surface for `SIMPLE` only. It may aggregate execution,
  harvest, custody, reports, variance, and read-only financial posture into one entry surface, but
  it must not become a second write path or a duplicate policy resolver.
- `/inventory/custody` is a mode-aware workspace over the same custody APIs and inventory truth.
  It must not create a separate sub-inventory engine or a duplicate settlement model.

## Cycle Matrix

| Workflow | Status | `SIMPLE` | `STRICT` |
|----------|--------|----------|----------|
| Daily Execution Smart Card Stack | implemented with canonical stack contract | plans, execution, materials, labor, irrigation, machinery, fuel posture, control, variance, burn rate, summarized cost posture | same path plus fuller financial trace and governed detail visibility |
| Petty Cash | implemented | request state, purpose, settlement-due posture, exception flags | request, approval, disbursement, settlement, liability balancing |
| Receipts and Deposit | implemented | collection/deposit posture, pending items, anomalies | treasury and deposit trace over the same collection truth |
| Supplier Settlement | implemented | payable state, delay, approval posture, summarized amounts | review, approval, payment, reconciliation, posting trace |
| Finance / Shadow Journal | implemented | append-only shadow daily journal visibility as read-only trace over the same ledger truth; no authoring or treasury mutation | governed ledger root, treasury, approvals, and full financial route tree |
| Contract Operations | implemented | posture-only dashboard, touring assessment state, rental/share readiness, summarized economic posture, risk | settlement mode, receipts, rent payment trace, reconciliation, and governed approval posture |
| Fixed Assets | implemented with seeded runtime evidence | register, assignment posture, depreciation health, summarized values | capitalization posture, depreciation trace, audit, fixed-asset register |
| Fuel Reconciliation | implemented with seeded runtime evidence | machine card, expected vs actual fuel, anomalies, summarized risk posture | reconciliation posture, treasury or inventory trace visibility, governed detail |
| Reports / Inventory Import-Export Platform | wave-2 and wave-3 registry implemented over the first-wave base | `Reports Hub` catalog for execution, variance, perennial, readiness, and posture-safe inventory reports; Arabic RTL `XLSX` first, optional `JSON`, operational inventory imports only | same catalog plus governed-heavy module-local export centers for fuel, fixed assets, contracts, suppliers, petty cash, receipts/deposit, and governance queues; strict-only inventory master/opening-balance templates remain backend-enforced |
| Planning Import Platform | implemented over the central import/export pipeline | `planning_master_schedule` and `planning_crop_plan_structure` through backend preview/apply only; no authoritative frontend parsing | same operational templates plus `planning_crop_plan_budget`; budget import remains strict-only and role-gated |
| Auth / Governance | implemented | scoped roster visibility, strict-mode warnings, non-financial posture | explicit user/group/governance mutation controls |

## Policy Fields

The current mode-aware workflows rely on these fields:

- `mode`
- `variance_behavior`
- `cost_visibility`
- `approval_profile`
- `contract_mode`
- `treasury_visibility`
- `fixed_asset_mode`

## Reference Integrity

- Implemented workflows must appear in `AGENTS.md`, doctrine, and core skills.
- Planned workflows must be labeled planned; they must not be implied complete.
- If doctrine lags behind code, the reference layer is not `100/100`.

## Canonical Policy Resolution

- Shared dashboards and mode-aware APIs should resolve defaults through the central mode-policy resolver service instead of copying fallback dictionaries by hand.
- Daily execution read surfaces now consume `smart_card_stack` as the canonical task-driven contract; legacy fields such as `task_focus` remain compatibility-only and must not be used by new UI surfaces.
- Fixed-assets and fuel dashboards now resolve through dedicated read-model services so policy interpretation stays centralized and reusable.
- SIMPLE must be able to open mode-aware contract, fixed-asset, and fuel dashboards without exposing governed financial mutation controls.
- SIMPLE may also open the finance hub as a read-only shadow journal surface, but it must not call governed `/finance/ledger/` authoring routes or imply that SIMPLE owns full ERP finance controls.
- Governed fixed-asset capitalization/disposal and fuel reconciliation posting must remain backend-owned service actions with `X-Idempotency-Key`, while SIMPLE stays posture-only.
- Import/export workflows must remain backend-governed and service-layer only. Uploading an Excel file must not directly write transactional rows before validation and apply.
- User-facing business files in this platform are `XLSX` first and Arabic RTL first. `JSON` is optional for integration. This first wave does not expose `CSV` in the user-facing contract.
- Wave 2 and Wave 3 export catalogs must remain registry-driven through the central import/export platform. Module-local dashboards may host export actions, but they must not fork into dashboard-specific export engines.
- Planning imports now follow the same platform contract. `MasterPlanImportModal`, `BudgetImportModal`, and `CropPlans` are wrappers over import jobs, not authoritative workbook parsers.

## Reports Hub Contract

- `/api/v1/advanced-report/` direct `GET` without explicit `section_scope` is a conservative
  compatibility contract and must return a usable payload containing `summary + details`.
- `section_scope` activates sectional optimization only when the client sends it explicitly.
- Frontend consumers must keep the helper split:
  - `buildAdvancedReportParams()` for conservative legacy/direct payloads
  - `buildAdvancedReportParamsWithSections()` for async sectional loading
- Tree-aware report requests may still set `include_tree_inventory=true` without forcing sectional
  loading; tree filters remain valid in both conservative and sectional paths.
- `Reports Hub` and `/finance/advanced-reports` must remain on the same backend reporting truth and
  must not diverge into separate reporting engines or separate result schemas.
- `/reports` remains a read/generation surface only. It may link users to operational entry
  surfaces such as `/daily-log/harvest`, but it must never become a write-authoring surface for
  daily execution.
- In `SIMPLE`, `/reports` may expose fixed operational presets such as daily execution, harvest,
  custody/materials, variance, and financial posture, provided those presets only reframe the same
  reporting truth and do not create a separate reporting engine.

## SIMPLE Operational Choreography

- `SIMPLE` should present one coherent operational journey:
  1. execution through `DailyLog`
  2. harvest through `/daily-log/harvest`
  3. accepted-balance material posture through `/inventory/custody`
  4. variance and alert follow-up through read-only control surfaces
  5. reporting through `/reports`
  6. read-only financial posture through the shadow-ledger surface when policy exposes it
- `DailyLog` remains the canonical write path for execution and harvest-capable activities.
- `CustodyWorkspace` in `SIMPLE` should emphasize accepted balance, incoming transfers, return
  posture, and queue state, while suppressing warehouse-authoring patterns reserved for governed
  surfaces.
- `Reports Hub` in `SIMPLE` should behave as a follow-up surface for the same daily execution truth,
  not as a destination disconnected from the execution cycle.
- Offline state should remain visible inside the main `SIMPLE` surfaces, not only in a standalone
  diagnostics panel, so field users can understand whether work is queued, synchronized, or
  conflicted without leaving the operational journey.

## Offline Transactional Taxonomy

- Transactional offline replay must be Dexie-backed and queue-aware.
- The canonical transactional queues are:
  - `generic_queue`
  - `harvest_queue`
  - `daily_log_queue`
  - `custody_queue`
- `lookup_cache` remains non-transactional read cache only. It must not be treated as a replay
  queue or as a fallback mutation store.
- `flushQueue()` is the unified sync orchestrator for transactional replay. Compatibility wrappers
  such as `SyncManager` may trigger it, but they must not keep an independent replay engine or a
  second source of transactional truth.
- Failed transactional items must remain visible through the same diagnostics surface with clear
  queue labels, retry posture, and dead-letter status.
- `DailyLog` offline persistence must separate mutable local drafts from immutable replay envelopes:
  - `daily_log_drafts` for resumable local work
  - `daily_log_queue` for append-only replay jobs
- Location-aware perennial lookups must remain scoped offline as well as online. Falling back to
  crop-wide cached data is acceptable only as an explicit warning state, never as a silent blind
  replacement for location-aware execution coverage.

## Governance Display and Canonical Units

- User-facing governance surfaces must be Arabic-first:
  - prefer Arabic full names when available
  - keep `username`, `slug`, and permission codenames as technical metadata only
  - do not expose technical identifiers as the primary label on memberships, users, groups, or
    role-template cards
- Critical authoring surfaces must consume canonical units only:
  - `DailyLog` material lines
  - harvest entry
  - inventory issue/receipt entry
- Free-text `UOM` input may remain only as explicit legacy compatibility display and must not stay
  on the active authoring path.
