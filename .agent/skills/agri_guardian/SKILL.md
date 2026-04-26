---
name: agri_guardian
description: Canonical operating checklist for AgriAsset architecture, V21 dual-mode governance, sector approval integrity, smart-card-stack canon, and release-gate readiness.
---

# Agri Guardian

Role: primary guardian for architecture, operations, frontend, doctrine, and release governance.
Status: Evidence-gated. Determine the live score only from `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`; do not hardcode calendar-based score claims in this skill.

## 1. Canonical Contract
- Follow [docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md](../../../docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md): `PRD V21` governs product truth, [AGENTS.md](../../../AGENTS.md) governs repo execution and evidence protocol, and skills remain execution lenses only.
- Use [docs/reference/REFERENCE_MANIFEST_V21.yaml](../../../docs/reference/REFERENCE_MANIFEST_V21.yaml) as the loading map, not as a replacement for precedence. Deeper `AGENTS.md` files outrank root `AGENTS.md` inside their subtrees.
- Keep the active skill set minimal. Add `schema_guardian`, `financial_integrity`, `auditor`, `startup_sentinel`, or `agri_maestro` only when scope requires them.
- Use service-layer writes only.
- Preserve `farm_id`, `cost_center`, and `crop_plan` on every sensitive mutation path that supports them.
- Treat any blocked command or blocked doctrine file as `BLOCKED`, not `PASS`.

## 1A. Prompt Review Checklist
When reviewing or authoring an operator prompt, verify all of the following before treating it as compliant:
- precedence correctness: `PRD -> deeper AGENTS -> root AGENTS -> canonical skills -> doctrine/reference aids -> code`
- evidence gate correctness: high claims require code anchors, test anchors, gate anchors, and runtime evidence anchors
- dual-mode correctness: `SIMPLE` stays technical and `STRICT` stays governed over the same truth chain
- governance chain correctness: farm-size and sector-chain claims must respect the active approval ladder
- block-vs-pass correctness: missing runtime evidence, blocked gates, or blocked smoke commands must be scored `BLOCKED`

Treat a prompt as non-compliant if it:
- places root `AGENTS.md` above a deeper `AGENTS.md`
- promotes doctrine, readiness matrices, or reference matrices above `AGENTS.md` without an explicit manifest override
- treats skills as higher-order truth instead of execution lenses
- allows `100/100` with active debt, reference conflict, blocked runtime proof, or gate failure

## 2. V21 Dual-Mode Contract
- `FarmSettings` is the primary source of truth for `SIMPLE/STRICT` behavior.
- `SIMPLE` is a technical agricultural control mode:
  - plans
  - materials
  - `DailyLog`
  - smart cards
  - variance and approval posture
  - agronomic/control reporting
  - summarized risk posture for finance-facing workflows
  - read-only shadow journal visibility in `/finance` when policy exposes the finance hub
- `STRICT` is full governed ERP over the same truth:
  - treasury
  - receipts and deposit
  - petty cash
  - supplier settlement
  - contract settlement
  - fixed assets
  - fuel reconciliation
  - sector approval chain
  - evidence lifecycle controls
- Do not split modes into duplicate transactional models or duplicate posting engines.
- Reject designs that leak full ERP authoring into `SIMPLE` unless a documented exception is explicitly part of the farm policy.
- A SIMPLE finance surface may reuse the same ledger truth chain for read-only shadow-entry visibility, but it must not reopen governed `/finance/ledger/` authoring routes, treasury mutation, or settlement posting.

## 3. Farm-Size Governance Contract
- `SMALL`: one local finance officer is allowed only as an explicit policy exception with compensating controls.
- `MEDIUM/LARGE`: a dedicated farm finance manager is required.
- Sector governance in `STRICT` should reflect the full chain:
  1. `محاسب القطاع`
  2. `مراجع القطاع`
  3. `رئيس حسابات القطاع`
  4. `المدير المالي لقطاع المزارع`
  5. `مدير القطاع` when policy requires business final approval
- Refuse designs that collapse the chain into one role while claiming final governed readiness.

## 4. Daily Execution Smart Card Stack Contract
Canonical flow:
`CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`

- `CropPlan` is the planning source of truth.
- `Activity` is the operational source of truth.
- The smart card stack is read-side only.
- Daily Logs must map to exactly one `CropPlan`.
- Legacy compatibility fields inside `DailyLog` may remain temporarily for compatibility:
  - `daily_achievement`
  - `control_metrics`
  - `variance_metrics`
  - `ledger_metrics`
  - `health_flags`
- The canonical read-side contract is `smart_card_stack`.
- `smart_card_stack` must be derived from `Activity.task_contract_snapshot` first, with fallback to the live `Task.task_contract` only for legacy activities missing a valid snapshot.
- One `Activity` still maps to one `Task`; multi-card behavior must not split into multiple transactional tasks.
- Frontend execution surfaces must be stack-first:
  - `DailyLog` and `ServiceCards` consume `smart_card_stack` as the primary contract
  - legacy smart-card fields are compatibility-only and may only power explicit legacy fallback paths
- Dynamic cards must be driven by backend `task_contract`; `archetype` is only a seed/preset, not the final contract by itself.
- `FarmSettings.show_daily_log_smart_card` is the farm-policy gate for rendering the smart context in `DailyLog`.
- `FarmSettings.allow_creator_self_variance_approval` is a narrow exception for critical variance approval only; it must never relax final-log maker-checker separation.
- `/daily-log/harvest` is a launch alias for discoverability only. It must redirect into the same
  canonical `DailyLog` write path and must not create a second harvest-authoring workflow.
- `/simple-hub` may exist as a `SIMPLE`-only orchestration surface that links execution, harvest,
  custody, reports, variance, and read-only financial posture into one operational entry point.
  It must remain frontend-only choreography over the same truth chain and must not create a second
  write path, duplicate policy resolver, or ERP-lite mutation surface.
- `/inventory/custody` may expose a mode-aware custody workspace, but it must remain a thin UI
  layer over the existing custody APIs and accepted-balance truth.
- This workflow must not depend on QR.
- Activity edits must reconcile operational state and use reversal plus re-posting for financial corrections.
- Tree transitions (Individual and Bulk): Cohort state updates (e.g. `JUVENILE` to `PRODUCTIVE`) must be strictly audited. In the event of transitioning to `EXCLUDED`, the deletion is blocked unless handled gracefully via a `TreeCensusVarianceAlert` mechanism instead of raw deletion.
- Routine negative `tree_count_delta` generates variance and managerial trace. It does not perform impairment.
- Extraordinary tree deaths must use Axis 18 `Mass Casualty Write-off`.
- Perennial variety selection must be location-aware. Multi-location execution uses union-with-coverage semantics, not a crop-wide blind list and not a forced intersection.
- `DailyLog` perennial statistics and `tree-census` summary must align on `LocationTreeStock.current_tree_count` as the current operational balance. `BiologicalAssetCohort` alive totals are reconciliation context and should surface as explicit gaps when they diverge.
- Direct current-balance entry for perennials belongs to the audited tree-inventory administrative adjustment path. `DailyLog` remains delta-only and must not become a direct current-balance authoring surface.
- Multi-location perennial service rows must remain row-location-specific on submit. Never collapse `service_counts.location_id` to the first selected location.
- `DailyLog` write-side must normalize `effective_task_contract` into a task-aware entry context before rendering sections or submitting payloads.
- Labor entry in `DailyLog` is task-contract-aware. Disabled labor cards must suppress labor validation and scrub stale labor fields before submit.

## 5. Contract Operations Rule
- Sharecropping, touring, and rental are economic/contract workflows, not technical crop execution.
- Touring is assessment-only and must anchor to harvest/production truth.
- `SIMPLE` exposes posture and risk; `STRICT` exposes settlement and governed trace.

## 6. Attachment Lifecycle Rule
- Approved authoritative finance evidence is archived and retained; it is not rapidly deleted after final approval.
- Only transient or duplicate working files may expire on TTL.
- When reviewing changes, require doctrine and metadata coverage for attachment class, archive state, and purge policy.

## 7. Engineering Checklist
- Use `Decimal`, never `float()`, in finance and inventory code.
- Reject financial mutations without `X-Idempotency-Key`.
- Avoid bare `except Exception`; map to explicit exceptions or let failures bubble.
- Enforce RTL-safe UI and stable selectors for mode-aware flows.
- For the first-wave import/export platform, treat `XLSX` as the primary business-facing format, keep `JSON` optional, and do not reopen `CSV` as the user-facing contract.
- For the expanded wave-2 / wave-3 report registry, keep `Reports Hub` and module-local export centers on the same backend platform, with `XLSX` first, optional `JSON`, mode-aware visibility, and no duplicate export engines.
- Reporting contract discipline:
  - direct `GET /api/v1/advanced-report/` without explicit `section_scope` is a conservative
    compatibility contract and should return a usable payload with `summary + details`
  - `section_scope` enables sectional optimization only when explicitly sent by the caller
- keep conservative helpers and sectional helpers distinct; do not silently force all consumers
    into the sectional path
- in `SIMPLE`, prefer one coherent user journey:
  - `DailyLog` remains the canonical write path
  - `/daily-log/harvest` is a shortcut into the same write path
  - `/inventory/custody` shows accepted-balance posture and queue state
  - `/reports` stays read-only but may expose fixed operational presets and CTAs back into
    execution and custody
  - `/finance` in `SIMPLE` remains shadow-ledger posture only when policy exposes it
- favor Arabic-first display on user-facing governance surfaces:
  - show Arabic full name first when available
  - demote `username`, `slug`, and permission codenames to technical metadata
- keep governance cards, memberships, users, groups, and role-template summaries free from
    English-first identity labels unless the user explicitly opens a technical metadata view
- keep offline transactional replay on Dexie-backed queues only:
  - `generic_queue`
  - `harvest_queue`
  - `daily_log_queue`
  - `custody_queue`
- for `DailyLog`, keep mutable local drafts separate from immutable replay envelopes:
  - `daily_log_drafts` stores resumable local work
  - `daily_log_queue` stores append-only replay jobs with their own `uuid`
- require offline lookup freshness posture on `DailyLog` when the page falls back to cached
  farm/crop/location/task data, especially for location-aware perennial execution
- treat `lookup_cache` as non-transactional cache only, not as a mutation queue
- use `flushQueue()` as the unified replay orchestrator; compatibility wrappers may trigger it but
  must not maintain independent replay logic
- require canonical-unit authoring on `DailyLog`, harvest, and inventory mutation forms; free-text
  `UOM` may remain only on read-only compatibility paths
- Treat planning imports as platform-governed too: `planning_master_schedule` and `planning_crop_plan_structure` are mode-aware operational templates, while `planning_crop_plan_budget` is `STRICT`-only. Frontend workbook parsing may assist UX only if it never becomes authoritative; preview/apply truth remains in backend.
- Keep shadow accounting automatic in `SIMPLE`.
- Treat rejected logs as editable by reopening to `DRAFT`.

## 8. Required Evidence by Workflow
Use [docs/doctrine/VERIFICATION_COMMANDS_V2.md](../../../docs/doctrine/VERIFICATION_COMMANDS_V2.md) as the current readable command reference.

At minimum:
- general release gate for schema, idempotency, float, scope, docs, and DR evidence
- workflow-specific gates for:
  - daily execution smart card
  - petty cash
  - receipts and deposit
  - supplier settlement
  - contract operations
  - fixed assets
  - fuel reconciliation
- `check_compliance_docs.py` when doctrine, skills, or PRD baseline changes
- do not treat `100/100` as proven unless `python backend/manage.py verify_axis_complete_v21` finishes with `overall_status=PASS` and `axis_overall_status=PASS`
- expanded SIMPLE browser/runtime bundles may be recorded as supplemental readiness evidence, but they do not replace the canonical score authority of `verify_axis_complete_v21`
- import/export platform bundles may be recorded as supplemental readiness evidence, but they do not replace the canonical score authority of `verify_axis_complete_v21`
- wave-2 / wave-3 export catalogs must remain grouped by registry metadata (`report_group`, `mode_scope`, `role_scope`, `sensitivity_level`, `ui_surface`) rather than frontend-only constants

## 9. Reference Integrity
- Doctrine must be readable and current.
- A workflow implemented in code but missing from doctrine or skills is a reference failure.
- V21 PRD, sector chain doctrine, attachment lifecycle doctrine, and execution doctrine must stay aligned.
- On Windows root shells, load backend PostgreSQL credentials through `scripts/windows/Resolve-BackendDbEnv.ps1` before Django smoke or test commands.
- For canonical Playwright verification on Windows, preload DB env and run migrations before
  backend `runserver`; browser proofs must not rely on a developer-local pre-migrated database.
- Treat `DOCX_CODE_TRACEABILITY_MATRIX_V10.md` as the active documentary traceability matrix; earlier V3-V9 matrices are historical snapshots only.
- fixed assets and fuel reconciliation now require governed action tests plus seeded runtime evidence before they can be treated as closed in the reference layer.
- do not claim `100/100` unless `npm --prefix frontend run test:ci` passes end-to-end and the readiness run shows seeded outbox success, retryable, and dead-letter evidence.
- for final score claims, require `verify_axis_complete_v21` as the canonical closure command in addition to the workflow/runtime evidence above

## 10. Refusal Triggers
Refuse changes that:
- remove `farm_id` isolation or RLS
- add `UPDATE` or `DELETE` behavior to `FinancialLedger` or `AuditLog`
- bypass `X-Idempotency-Key` for financial mutations
- introduce `float()` into finance or inventory math
- treat a smart card as a write path
- route mass casualty write-offs through ordinary Daily Log edits
- expose the full strict sector chain to simple mode without documented policy
- purge authoritative approved financial evidence as if it were transient cache data

## 11. Expected Review Output
When reviewing or scoring:
- state whether evidence is `PASS`, `BLOCKED`, or `FAIL`
- call out the exact broken contract
- separate operational truth, variance truth, and ledger truth
- do not claim `100/100` without command output, tests, or code trace


## V15 Phase-2 Focus
- enforce queue-aware approval inbox readiness
- require maintenance-cycle command coverage for approvals, remote reviews, and evidence lifecycle
- require archive/quarantine metadata parity when attachment lifecycle evolves


## V15 delta
- V15 mode/authority contract.
- SIMPLE must not auto-register full finance routes.
- STRICT final posting actions honor `approval_profile` and may require sector-final authority.


## V16 Addendum
- Respect profile-aware approval chains and avoid collapsing `basic`, `tiered`, and `strict_finance` farms into one synthetic ladder.
- Treat `run_governance_maintenance` as the canonical operational entrypoint for overdue approvals, remote-review drift, and attachment lifecycle queues.


## V17 update
- Respect forensic approval timelines: when reviewing `ApprovalRequest`, inspect `ApprovalStageEvent` evidence and ensure UI/API expose stage-event trace instead of relying on current state alone.


## V18 Addendum
- Verify `STRICT` role workbench visibility for sector lanes before claiming governance closure.
- Treat PDF JavaScript/OpenAction and XLSX macro/zip-bomb detection as hard upload-gate findings, not optional warnings.
- Remote-review governance maintenance must use `report_due_reviews()` and raise explicit backlog evidence for remote farms.


## V20 note
This skill must respect remote review escalation evidence and attachment lifecycle events when evaluating strict workflows.


## V21 Runtime and Forensic Closure
- V21 raises production readiness through a governed runtime probe, stronger attachment scanning hooks, and explicit role workbench attention counts.
- SIMPLE remains technical/variance-first; STRICT owns final financial authority, forensic evidence lifecycle, and sector escalation.
- Do not claim runtime completeness unless `manage.py check`, migrations, targeted backend tests, and smoke commands run successfully on a provisioned stack.


## V22 Database Policy
- **PostgreSQL is the sole permitted database engine.** SQLite is unconditionally banned for governance validation, testing, production, schema drift checks, and RLS policy verification.
- All schema inspections, migration health checks (`makemigrations --check --dry-run`), trigger audits, and RLS policy evaluations must be performed against a live PostgreSQL connection.
- On Windows, load credentials via `scripts/windows/Resolve-BackendDbEnv.ps1` before running any Django management command.
- A SQLite fallback suggestion or `test_settings_sqlite.py` usage is a **BLOCKED** finding — not a valid workaround.
- Runtime proof score is `BLOCKED` unless `python manage.py check` and `python manage.py showmigrations --plan` succeed against live PostgreSQL with zero issues.

## V22 Hardening and Offline Governance (2026-04-17)
- Axis 19 (Temporal Precision): Verify that activity templates and templates enforce sequence/duration windows.
- Axis 20 (Offline Sync Integrity): Enforce farm-specific retention logic and forensic audit logging for purge events.
- Axis 20.1 (Mobile Evidence Integrity): Enforce minimum GPS accuracy (50m) for field reports in STRICT mode. Use `GpsService.isLocationValid()` check.
- Axis 21 (Sovereign Mobile Field Audit): Verify role-aware 'Inbox' lanes, AI-enhanced image clarity (sanitizer pass), and 7-day local artifact retention (Axis 23).
- Reject any sync logic that bypasses the configurable purge thresholds in `FarmSettings`.
- Ensure `Media Purge` is available as an optional toggle to recover mobile storage safely.
## V21.5 Sovereign Finality (2026-04-18)
- Axis 21 (Finality): The system is formally certified via the **Shabwah Farm End-to-End Simulation**.
- 100/100 Score: Any score claim must be backed by both `verify_axis_complete_v21` and the 'Shabwah Genesis' record.
- Axis 18 (Mass Writeoff): High-risk writeoff events are tested in forensic conditions.
- GENESIS COMPLETE: The system has reached a production-ready, forensic-hardened baseline.
