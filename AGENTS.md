# AgriAsset Agents Protocol
## Version: 5.1.0 (Shabwah Genesis Edition - 2026-04-18)

> [!IMPORTANT]
> SYSTEM STATUS: **CERTIFIED 100/100**. This repository has achieved full operational maturity across all 18 axes of compliance.
> Strict no-regression mode is active. Any change that lowers a verified axis must be rejected.

> [!NOTE]
> CHANGELOG v4.1.2: live score authority remains the latest canonical `verify_axis_complete_v21` summary under `docs/evidence/closure/latest/`. Historical reports, handoff packs, and skills must not outclaim current canonical evidence.

---

## Identity and Scope
- System: AgriAsset (YECO Edition)
- Owner: Yemeni Economic Corporation - Agriculture Sector
- Model: Hybrid Government Resource Planning (GRP)
- Context: Northern Yemen, weak internet, manual entry as source of truth
- Scope: entire repository; deeper `AGENTS.md` files override inside their subtrees
- Terminology: [docs/GLOSSARY.md](docs/GLOSSARY.md)

## Reference Governance
- Product truth and acceptance truth are governed by [docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md](docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md).
- Repository execution protocol and evidence gating are governed by this root `AGENTS.md`.
- Canonical reference precedence is defined in [docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md](docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md) and [docs/reference/REFERENCE_MANIFEST_V21.yaml](docs/reference/REFERENCE_MANIFEST_V21.yaml).
- Reference precedence is not the same thing as read order. `REFERENCE_MANIFEST_V21.yaml` is the canonical entry map for what to load, while `REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md` governs which active layer wins when references disagree.
- Readiness matrices, role matrices, attachment matrices, and other reference aids are required reading inputs, but they do not outrank `PRD`, a deeper `AGENTS.md`, or this root `AGENTS.md` unless the active manifest explicitly says so.
- Skills are execution lenses only; they may not override the PRD or `AGENTS.md`.
- Historical PRD and doctrine files remain useful for traceability, but they are not active higher-order references when they conflict with V21.

---

## Core Operating Rules
1. Service layer only: views and tasks never write transactional rows directly.
2. Decimal only: `float()` is banned in finance and inventory logic.
3. Strict UI validation: non-delta numeric inputs must enforce non-negative input.
4. Idempotency V2: all financial `POST/PATCH` operations require `X-Idempotency-Key`.
5. Append-only ledger: no `UPDATE` or `DELETE` on `FinancialLedger`.
6. Tenant isolation: every transactional row carries `farm_id`; scope must hold in Python and PostgreSQL.
7. Database Engine: PostgreSQL is the sole permitted database engine. SQLite is strictly banned for governance validation, testing, and production environments. All schema inspections, RLS policies, and triggers must be evaluated against a live PostgreSQL connection.
8. RTL first: React/Vite layouts must support Arabic RTL and dark mode.
9. Explicit error handling only: use `ValidationError`, `PermissionDenied`, or concrete DB exceptions. Never swallow bare `except Exception`.
10. Surra law: labor costing is daily-rate based, not hourly payroll.
11. Analytical purity: `FinancialLedger` rows require `cost_center` and `crop_plan` when the business object supports them.
12. Rejected logs must support reopening back to `DRAFT`.
13. Dual-mode ERP: `SIMPLE` hides explicit ledger authoring while backend posts shadow accounting; `STRICT` exposes full ERP controls.
14. Feature toggles such as Zakat, depreciation, sharecropping, petty cash, and attachment policy classes must be tenant-configurable and enforced in backend rules.
15. Simple-mode route breaches must emit `AuditLog`, not just redirect.
16. Simple-mode agronomy dashboards may expose burn-rate style ratios without leaking forbidden absolute finance values.
17. Strict single-crop costing: each `DailyLog` maps to exactly one `CropPlan`.
17. Petty cash settlement: cash labor batches must post interim `WIP Labor Liability` and settle against a voucher.
18. Mass exterminations: extraordinary tree deaths must use a dedicated `Mass Casualty Write-off` workflow linked to IAS 41 impairment. However, `Bulk Cohort Transition` APIs may be used to transition multiple cohorts to EXCLUDED when authorized by policy, generating `TreeCensusVarianceAlert` events instead of raw deletion.
19. Farm-size governance: `SMALL` farms may use a single local finance officer only under compensating controls; `MEDIUM/LARGE` farms require a dedicated farm finance manager.
20. Sector governance: sector approval is multi-level in `STRICT` and must not collapse into one overpowered role.
21. Contract operations doctrine: sharecropping, touring, and rent settlement are not technical crop execution; touring is assessment-only and anchored to harvest/production truth.
22. Attachment lifecycle doctrine: approved authoritative financial evidence is archived and retained, not quickly deleted; only transient duplicates, cache copies, and draft artifacts may expire on TTL.
23. `SIMPLE` is a technical agricultural control surface, not a diluted ERP authoring surface.
24. Profiled final posting authority: farms using `approval_profile=strict_finance` require sector-final authority for final financial posting actions in supplier settlement, petty cash disbursement/settlement, fixed assets, fuel reconciliation, and contract payment posting.
25. Admin convenience must not silently reopen full financial route trees in `SIMPLE`; finance route registration follows the effective mode contract.
26. Perennial Asset Enhancements (Phase 10): System modules such as Tree GIS, Bulk Transitions, and Biocost Depreciation Predictor are gated explicitly by `FarmSettings` (`enable_tree_gis_zoning`, `enable_bulk_cohort_transition`, `enable_biocost_depreciation_predictor`).
27. Forensic approval timeline: every approval request in `STRICT` must leave stage-event evidence (`created`, `stage approved`, `final approved`, `rejected`, `auto escalated`) that can be queried independently from the mutable UI state.
28. Sector role workbench: `STRICT` governance must expose grouped workload visibility for sector accountant, reviewer, chief accountant, finance director, and sector director lanes.
29. Attachment intake hardening: PDF JavaScript/OpenAction markers and XLSX macro or zip-bomb patterns must be blocked or quarantined before evidence becomes authoritative.

---

## Daily Execution Smart Card Contract

Canonical path:
`CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`

- `CropPlan` is the planning source of truth.
- `Activity` is the operational source of truth.
- The smart card stack inside `DailyLog` is read-side only. It must not create, mutate, or approve ledger rows directly.
- `FarmSettings.show_daily_log_smart_card` is the farm-level visibility gate for the `DailyLog` smart context. When disabled, the daily log must remain functional through the core technical fields without rendering smart-card UI.
- Perennial variety selection in `DailyLog` must be location-aware. For multi-location execution, the frontend should consume the union of available varieties with explicit coverage metadata (`location_ids`, `available_in_all_locations`) rather than a crop-wide blind list.
- `DailyLog` perennial variety stats and the `tree-census` summary must align on `LocationTreeStock.current_tree_count` as the canonical current operational balance. Cohort alive totals are reconciliation context and must not silently replace the current stock balance.
- **Stock Synchronization Doctrine**: The Daily Log API (`get_available_varieties_by_location`) must decouple from `BiologicalAssetCohort` and rely exclusively on `LocationTreeStock`. System must guarantee record presence via database signals (`sync_location_tree_stock_for_cohort`) when cohorts are instantiated to avoid Read-Model fusion.
- Multi-location perennial service rows must persist `location_id` per row. Union-with-coverage is a selection aid only; submitted `service_counts` remain row-location-specific and must not collapse silently to the first selected location.
- `DailyLog` write-side must normalize `effective_task_contract` into a task context that governs visible sections, labor policy, perennial behavior, and submit-time scrubbing.
- Labor inputs in `DailyLog` are task-contract-aware. When the `labor` card is disabled, the labor step becomes non-operative and stale labor payload fields must be scrubbed before submit.
- Legacy compatibility fields for this workflow remain:
  - `plan_metrics`
  - `task_focus`
  - `daily_achievement`
  - `control_metrics`
  - `variance_metrics`
  - `ledger_metrics`
  - `health_flags`
- The canonical UI contract is `smart_card_stack`.
- Each `smart_card_stack` entry must expose:
  - `card_key`
  - `title`
  - `enabled`
  - `order`
  - `mode_visibility`
  - `status`
  - `metrics`: must include `total_cost` and `total_achievement` (Ingaz) for labor cards, and `actual_qty`/`actual_cost` for materials.
  - `flags`
  - `data_source`
  - `policy`
  - `source_refs`
- `smart_card_stack` must be derived from `Activity.task_contract_snapshot` first, with fallback to the live `Task.task_contract` only for legacy activities missing a valid snapshot.
- One `Activity` still maps to one `Task`; multi-card behavior must not split into multiple transactional tasks.
- **Dynamic UX Mandate**: The frontend UI (`/crops/tasks`, `DailyLog`) MUST NOT use static capability assumptions. Task creation may start from an `archetype` seed or crop preset, but the saved task must persist an explicit `task_contract` that drives the exact Smart Cards rendered in execution.
- **Archetype Integration Policy**: Modules communicating with DailyLog (e.g., TreeCensus Launchpad) MUST pass strict `archetype` keys (e.g., `BIOLOGICAL_ADJUSTMENT`) instead of localized hardcoded task names. The target UI must resolve the task internally using the archetype to ensure localization safety and strict capability enforcement.
- Task creation remains `one Task -> one Activity`, but a single task may enable multiple smart cards inside the same execution contract.
- This workflow does not depend on QR for technical execution; QR remains an optional selection aid.
- GPS Evidence: Mandatory for all Daily Logs in STRICT mode or when `enable_tree_gis_zoning=true`. Submissions without valid coordinates (Accuracy <= 50m) are blocked or quarantined.
- Costing is computed on the backend from technical inputs only.
- Activity edits must reconcile operational state and use reversal plus re-posting for financial corrections.
- Tree transitions (Individual and Bulk): Cohort state updates (e.g. `JUVENILE` to `PRODUCTIVE`) must be strictly audited. In the event of transitioning to `EXCLUDED`, the deletion is blocked unless handled gracefully via a `TreeCensusVarianceAlert` mechanism that cascades up for anomaly correction.
- Routine tree add/update/death may appear in daily execution:
  - positive delta: operational addition/reconciliation
  - negative delta: descriptive operational evidence that must generate variance and managerial trace
- Routine negative `tree_count_delta` must not be treated as a capital impairment shortcut.
- Extraordinary mass tree deaths must leave Daily Log correction flow and enter Axis 18 `Mass Casualty Write-off`.

---

## Sovereign Desktop Expansion (Axis 21.D)

- **Target**: Windows (Win32/Flutter).
- **Identity**: `AgriAsset Sovereign Field Command`.
- **Status**: **Integrated 100/100**.
- **Governance**:
  - Desktop-grade window orchestration (1280x800).
  - Platform-gated sync logic (Registry-safe secure storage).
  - No legacy regression: Android build stability is guaranteed and verified.
- **Deployment**:
  - Requires Visual Studio 2022 with "Desktop development with C++" workload.
  - Command: `flutter build windows --release`.

---

## Dual-Mode Operating Contract

`FarmSettings` is the primary source of truth for operational mode and policy behavior at the farm level.

- `FarmSettings.mode` controls the effective user-facing contract per farm.
- `SystemSettings.strict_erp_mode` may remain as a legacy global override or bootstrap signal, but it is not the primary contract for new dual-mode workflows.
- `SIMPLE` means a technical agricultural control system:
  - plans
  - materials
  - `DailyLog`
  - smart card stack
  - variance and approval posture
  - agronomic and control reports
  - summarized risk and readiness posture for finance-related workflows
  - lightweight operational attachments only when policy allows
- `STRICT` means full governed ERP over the same backend truth:
  - treasury
  - receipts and deposit
  - petty cash
  - supplier settlement
  - contract operations settlement
  - fixed assets
  - fuel reconciliation
  - multi-level sector approvals
  - evidence retention and archive controls
- Finance route registration must follow the effective farm mode even for admin/superuser surfaces; emergency access is a separate operational control, not a default route-registration bypass.
- Frontend mode-aware surfaces must preserve the same read contract and same truth chain:
  - `DailyLog` and `ServiceCards` consume `smart_card_stack` first
  - `Petty Cash`, `Supplier Settlement`, `Contract Operations`, `Fixed Assets`, and `Fuel Reconciliation` remain posture-first in `SIMPLE`
  - the same surfaces may show governed detail in `STRICT`, but must not switch to a different business object model
- Both modes share the same truth chain:
  - `CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`
- Smart cards are read-side only in both modes.
- `SIMPLE` must preserve shadow accounting, auditability, and variance generation.
- `FarmSettings.allow_creator_self_variance_approval` may allow the creator of a `DailyLog` to self-approve a critical variance only under explicit farm policy. This exception does not permit self-approval of the final log and must leave append-only audit evidence.
- `STRICT` must preserve the same operational truth while exposing more approvals, finance trace, settlement controls, and evidence controls.
- A workflow may expose different UI surfaces by mode, but it must not fork into duplicate posting engines or duplicate truth tables.

---

## Farm-Size Governance Contract

### `SMALL`
- May operate with a single local finance officer when `single_finance_officer_allowed=true`.
- The same person may act as local accountant, chief accountant, and acting farm finance manager only when:
  - the farm is formally tiered `SMALL`
  - remote-site policy is enabled where relevant
  - local thresholds are enforced in backend rules
  - sector review remains mandatory above local thresholds and for final close
- `SMALL` farms must use compensating controls:
  - documented approval thresholds
  - weekly remote sector review
  - mandatory exception reporting
  - hard-close reserved for the sector chain

### `MEDIUM`
- Must have a dedicated `المدير المالي للمزرعة`.
- Farm-level accountant and chief accountant remain distinct from farm finance manager.
- `رئيس حسابات المزرعة` is the local accounting-review and soft-close-readiness role; it is not a substitute for the sector chief accountant.
- Sector chain provides review, escalation, and final governed approval.

### `LARGE`
- Must have a dedicated `المدير المالي للمزرعة` plus stronger internal segregation.
- Treasury, settlement, and period-close evidence must be more explicit.
- `رئيس حسابات المزرعة` remains a local review/control gate, not the final sector accounting sign-off.
- Sector chain acts as grouped oversight, consolidated review, and final policy gate.

---

## Sector Governance Contract

Sector governance is not “silent oversight only” and not “daily farm execution instead of the farm”. It is the multi-farm management and governed approval layer.

### Sector chain in `STRICT`
1. `محاسب القطاع`
2. `مراجع القطاع`
3. `رئيس حسابات القطاع`
4. `المدير المالي لقطاع المزارع`
5. `مدير القطاع` when business/executive final approval is required by policy

### Duties by design
- `محاسب القطاع`: first structured sector-side review, completeness, policy precheck, return-to-farm when incomplete
- `مراجع القطاع`: second-line review, maker-checker validation, anomaly challenge, exception escalation
- `رئيس حسابات القطاع`: accounting sign-off, reconciliation sign-off, close-readiness validation
- `المدير المالي لقطاع المزارع`: final financial approval for governed thresholds, exceptions, and hard-close
- `مدير القطاع`: final business/executive approval where policy, materiality, or exception class requires it
- `رئيس حسابات المزرعة`: local accounting review, local documentation quality, and soft-close readiness only; this role does not replace `رئيس حسابات القطاع`.

### Design restrictions
- Sector roles must not all collapse into a single overpowered finance role.
- Sector roles must not replace normal farm execution in ordinary daily work.
- `SIMPLE` should not expose the entire sector chain to ordinary field users.

---

## Operational Cycles by Mode

The following workflows are part of the V12 contract and must remain mode-aware:

- `Daily Execution Smart Card Stack`
  - `SIMPLE`: operational, variance, burn-rate, summarized cost visibility
  - `STRICT`: same operational truth plus fuller ledger and approval visibility
- `Petty Cash`
  - `SIMPLE`: request, state, exception, settlement-due posture
  - `STRICT`: request, approval, disbursement, settlement, liability balancing
- `Receipts and Deposit`
  - `SIMPLE`: collection and deposit posture, anomalies, risk state
  - `STRICT`: collection, treasury, deposit, and financial trace
- `Supplier Settlement`
  - `SIMPLE`: payable posture, delay, approval and variance summary
  - `STRICT`: review, approval, payment, reconciliation, and posting trace
- `Contract Operations`
  - `SIMPLE`: contract status, expected share or rent, touring status, production linkage, delays, and risk
  - `STRICT`: settlement mode, receipt trace, rent payment trace, reconciliation posture, final approval chain
- `Fixed Assets`
  - `SIMPLE`: asset register, assignment posture, depreciation health, summarized cost visibility
  - `STRICT`: capitalization posture, depreciation trace, book value, and fixed-asset controls
- `Fuel Reconciliation`
  - `SIMPLE`: machine card, expected vs actual fuel, anomaly state, summarized risk posture
  - `STRICT`: reconciliation posture, treasury or inventory trace visibility, governed detail
- `Attachments and Evidence`
  - `SIMPLE`: lightweight operational evidence only where policy allows
  - `STRICT`: evidence-class aware upload, archive, retention, and purge policy

The operational surface may differ by mode, but business truth must not split into duplicate models or duplicate posting logic.

---

## Contract Operations Doctrine

- Sharecropping, touring, and rental are contract/economic workflows, not technical crop execution workflows.
- Touring is assessment-only. It must anchor to production or harvest truth, not to technical execution control.
- Sharecropping must preserve physical-share vs financial-settlement policy behavior.
- `SIMPLE` exposes posture, readiness, expected share/rent, and anomalies.
- `STRICT` exposes settlement, receipt, payment, reconciliation, and governed approval trace.
- Contract operations must not create technical agronomy activities by themselves.

---

## Attachment Lifecycle Doctrine

Attachment handling must be policy-aware and evidence-safe.

### Attachment classes
- `transient`: draft uploads, duplicate cache copies, temporary working files; eligible for TTL purge or archive move
- `operational`: routine operational evidence retained per policy
- `financial_record`: authoritative approved finance evidence; archive and retain, do not rapidly delete
- `legal_hold`: no expiry until explicit release

### Required controls
- allowed extensions and size limits
- content verification and safe storage policy
- hash-based deduplication where feasible
- archive state and retention metadata
- purge only after policy checks pass
- delete local/temporary copies without deleting authoritative archived evidence

### Forensic scenario matrix
- `clean`: scanned clean, policy-compatible, may remain operational or become authoritative when workflow rules permit
- `quarantined`: blocked pending review or false-positive restoration path; must leave append-only events
- `archived`: authoritative evidence stored in archive tier with retention metadata
- `legal_hold`: retained without expiry until explicit release
- `restored`: false positive or released hold returned to an allowed active state with trace
- `purge_eligible`: transient or non-authoritative artifacts only, and only after policy checks pass

---

## Reference Integrity

`100/100` cannot be awarded when the reference layer is broken.

- Doctrine files must be readable, current, and aligned with implemented workflows.
- Release commands must match actual code paths and current tests.
- Final `100/100` claims must be backed by `python backend/manage.py verify_axis_complete_v21` with both `overall_status=PASS` and `axis_overall_status=PASS`.
- A workflow implemented in code but missing from doctrine or skills is a reference failure.
- Windows root-shell runtime verification should preload backend PostgreSQL credentials through `scripts/windows/Resolve-BackendDbEnv.ps1` before Django smoke or test commands.
- Historical traceability matrices `DOCX_CODE_TRACEABILITY_MATRIX_V3` through `V9` are superseded snapshots. `DOCX_CODE_TRACEABILITY_MATRIX_V10.md` is the active traceability reference.
- `docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md` is the active product baseline. Older PRD files remain historical baselines only unless explicitly cited for comparison.
- If a release-gate script is blocked by write-locked output files or environment limitations, the condition is `BLOCKED` unless alternative documented evidence is explicitly recorded in the readiness report.
- Review and evaluation prompts must treat missing runtime smoke, blocked gate execution, or unavailable targeted-test evidence as `BLOCKED`, not `PASS`.
- Prompt scaffolds become reference failures if they invert the active precedence order, place root `AGENTS.md` above a deeper `AGENTS.md`, or promote doctrine and matrix files over `AGENTS.md` without an explicit manifest override.
- Compatibility debt must remain labeled as transitional, not implied canonical:
  - legacy smart-card fields (`plan_metrics`, `task_focus`, `daily_achievement`, `control_metrics`, `variance_metrics`, `ledger_metrics`, `health_flags`) remain compatibility-only until a dedicated removal pass confirms no active consumer still requires them
  - historical PRD and doctrine files remain traceability baselines only and must not be cited as active references when V21 references disagree
  - frontend mode-aware pages must prefer stack-first rendering and use legacy smart-card fields only when the canonical stack is absent from a legacy payload

---

## Doctrine References

| Doctrine | File | Scope |
|----------|------|-------|
| Reference Precedence | [docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md](docs/reference/REFERENCE_PRECEDENCE_AND_OVERRIDE_V21.md) | reference-order and override policy |
| Reference Manifest | [docs/reference/REFERENCE_MANIFEST_V21.yaml](docs/reference/REFERENCE_MANIFEST_V21.yaml) | active canonical reference pack |
| Role / Permission Matrix | [docs/reference/ROLE_PERMISSION_MATRIX_V21.md](docs/reference/ROLE_PERMISSION_MATRIX_V21.md) | local vs sector role responsibilities by mode |
| Runtime Proof Checklist | [docs/reference/RUNTIME_PROOF_CHECKLIST_V21.md](docs/reference/RUNTIME_PROOF_CHECKLIST_V21.md) | runtime and release evidence checklist |
| Financial Rules | [docs/doctrine/FINANCIAL_DOCTRINE.md](docs/doctrine/FINANCIAL_DOCTRINE.md) | Fund accounting, fiscal lifecycle, Zakat, IAS 41 |
| Fiscal Period Operations UI | [docs/doctrine/FISCAL_PERIOD_OPERATIONS_UI.md](docs/doctrine/FISCAL_PERIOD_OPERATIONS_UI.md) | fiscal close UI routes, reopen workflow, year-opening maintenance |
| Hybrid Mode | [docs/doctrine/HYBRID_MODE_V2.md](docs/doctrine/HYBRID_MODE_V2.md) | current SIMPLE/STRICT behavior |
| V11 Governance and Mode Policy | [docs/doctrine/V11_GOVERNANCE_AND_MODE_POLICY.md](docs/doctrine/V11_GOVERNANCE_AND_MODE_POLICY.md) | mode boundaries, farm-size governance, sector chain |
| V11 Sector Governance and Approvals | [docs/doctrine/V11_SECTOR_GOVERNANCE_AND_APPROVAL_CHAIN.md](docs/doctrine/V11_SECTOR_GOVERNANCE_AND_APPROVAL_CHAIN.md) | roles, thresholds, approval ladders |
| V11 Attachment Evidence Lifecycle | [docs/doctrine/V11_ATTACHMENT_EVIDENCE_LIFECYCLE.md](docs/doctrine/V11_ATTACHMENT_EVIDENCE_LIFECYCLE.md) | upload classes, retention, archive, purge |
| V14 Stage-2 Operationalization | [docs/doctrine/V14_STAGE2_OPERATIONALIZATION.md](docs/doctrine/V14_STAGE2_OPERATIONALIZATION.md) | queue-aware approvals, maintenance cycle, attachment runtime metadata |
| V15 Profiled Posting and Mode Enforcement | [docs/doctrine/V15_PROFILED_POSTING_AND_MODE_ENFORCEMENT.md](docs/doctrine/V15_PROFILED_POSTING_AND_MODE_ENFORCEMENT.md) | governed final posting authority and stricter SIMPLE/STRICT finance route enforcement |
| V16 Approval Chain and Governance Maintenance | [docs/doctrine/V16_APPROVAL_CHAIN_AND_GOVERNANCE_MAINTENANCE.md](docs/doctrine/V16_APPROVAL_CHAIN_AND_GOVERNANCE_MAINTENANCE.md) | profile-aware chains, unified maintenance command, remote review and attachment maintenance summary |
| Verification Commands | [docs/doctrine/VERIFICATION_COMMANDS_V2.md](docs/doctrine/VERIFICATION_COMMANDS_V2.md) | current release gate and blockers |
| Dual-Mode Operational Cycles | [docs/doctrine/DUAL_MODE_OPERATIONAL_CYCLES.md](docs/doctrine/DUAL_MODE_OPERATIONAL_CYCLES.md) | implemented and planned workflows by mode |
| Daily Execution Smart Card Stack | [docs/doctrine/DAILY_EXECUTION_SMART_CARD.md](docs/doctrine/DAILY_EXECUTION_SMART_CARD.md) | non-QR execution, stack contract, tree-loss separation |
| Documentary Cycle | [docs/doctrine/DOCUMENTARY_CYCLE.md](docs/doctrine/DOCUMENTARY_CYCLE.md) | end-to-end flow |
| Strict Completion Matrix | [docs/doctrine/STRICT_COMPLETION_MATRIX.md](docs/doctrine/STRICT_COMPLETION_MATRIX.md) | workflow-to-code traceability and mode alignment |
| Glossary | [docs/GLOSSARY.md](docs/GLOSSARY.md) | domain terms |
| Master PRD | [docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md](docs/prd/AGRIASSET_V21_MASTER_PRD_AR.md) | active product requirements baseline |

---

## Skill Catalog

| Skill | Role | File | Trigger |
|:------|:-----|:-----|:--------|
| `agri_guardian` | Primary | `.agent/skills/agri_guardian/SKILL.md` | always active |
| `schema_guardian` | DBA | `.agent/skills/schema_guardian/SKILL_V2.md` | schema, RLS, attachment metadata, sequence integrity |
| `financial_integrity` | CFO | `.agent/skills/financial_integrity/SKILL.md` | costing, ledger, finance governance, period close |
| `auditor` | Forensic | `.agent/skills/auditor/SKILL.md` | scoring, traceability, fraud, approval chain evidence |
| `startup_sentinel` | DevOps | `.agent/skills/startup_sentinel/SKILL.md` | startup and environment repair |
| `agri_maestro` | Architect | `.agent/skills/agri_maestro/SKILL.md` | large refactors, V12 governance rollout |

Skill rules:
- `agri_guardian` is mandatory baseline.
- Optional skills supplement it; they never replace it.
- Canonical skill selection follows [docs/reference/SKILLS_CANONICALIZATION_V21.yaml](docs/reference/SKILLS_CANONICALIZATION_V21.yaml).
- `schema_guardian/SKILL_V2.md` is the canonical schema-governance skill.
- `schema_sentinel/SKILL_NEW.md` and `sql_sync/SKILL.md` remain conditional specialist skills; deprecated variants must not be cited as authoritative.
- Fiscal lifecycle route changes, reopen flows, and year-opening maintenance must keep
  `financial_integrity` aligned with `FINANCIAL_DOCTRINE.md` and
  `FISCAL_PERIOD_OPERATIONS_UI.md`.

---

## 18 Axes of Compliance

| # | Axis | Key Rule |
|:-:|:-----|:---------|
| 1 | Schema Parity | `showmigrations` clean, zero zombies and ghosts |
| 2 | Idempotency V2 | `X-Idempotency-Key` plus cache-replay |
| 3 | Fiscal Lifecycle | `open -> soft-close -> hard-close` |
| 4 | Fund Accounting | revenue to sector, expenses to budget |
| 5 | Decimal and Surra | zero `float()`, Surra day-rate only |
| 6 | Tenant Isolation | `farm_id`, Python guards, PostgreSQL RLS |
| 7 | Auditability | `AuditLog` on sensitive mutations |
| 8 | Variance and BOM | deviations and approvals are explicit |
| 9 | Sovereign and Zakat | Zakat and solar rules enforced |
| 10 | Farm Tiering | tier-based delegation and thresholds |
| 11 | Biological Assets | cohort integrity and IAS 41 |
| 12 | Harvest Compliance | idempotency, fiscal, audit, Zakat gate |
| 13 | Seasonal Settlement | WIP to COGS plus settlement trace |
| 14 | Schedule Variance | late or early activity becomes variance |
| 15 | Sharecropping | physical vs financial mode per settings |
| 16 | Single-Crop Costing | one `DailyLog`, one `CropPlan` |
| 17 | Petty Cash Settlement | WIP labor liability tied to voucher |
| 18 | Mass Exterminations | dedicated mass-casualty write-off flow |
| 19 | Temporal Precision | adherence to task sequencing and duration |
| 20 | Offline Sync Policy | automated health and forensic purge logs |

Full pass criteria are defined in `.agent/skills/agri_guardian/SKILL.md`.

---

## HR and Procurement

Employee categories:
- `OFFICIAL/GOV`: attendance only, no crop-cost capitalization
- `CASUAL/CONTRACT`: full crop-cost allocation via Surra
- `CASUAL_BATCH`: offline-friendly batch labor, no identity expansion

Procurement:
- below 500K: direct flow
- above 500K: committee and sector approval
- pesticide receiving requires agricultural engineer approval
- diesel requires dipstick versus ledger reconciliation
- solar depreciation posts `DR 7000-DEP / CR 1500-ACC-DEP`

---

## Offline and Weak-Network Protocol

- Frontend must generate `uuidv4()` idempotency keys for financial and capital-asset mutations.
- Same key must return the same economic result deterministically.
- Server state wins conflicts.
- Failed syncs route to `SyncConflict_DLQ`.
- `TreeCensus` remains offline-first with FIFO replay.
- Financial mutations are excluded from generic offline queues.
- Simple-mode Daily Logs may queue operational payloads offline and replay them into Shadow Accounting on reconnect.
- Late offline payloads that trigger critical financial variance must enter quarantine before ledger posting.
- Remote `SMALL` farms must support asynchronous review windows without weakening auditability or final close controls.

---

## Data Contract Standards

- Money uses `Decimal` with explicit precision and scale.
- Local units come from localized seed data, never hardcoded UI text.
- No IoT or sensor ingestion.
- Field APIs collect technical inputs only; backend computes financial values.
- QR remains optional for inventory or attendance selection aids.
- GPS Evidence Standard: Valid field reports require a minimum accuracy of 50m. Readings with lower accuracy are rejected as insufficient evidence for Axis 26 (Tree GIS).
- Attachments must carry evidence classification and retention metadata where policy requires it.

---

## Non-Functional Requirements

Performance and API:
- DRF throttling: `AnonRateThrottle`, `UserRateThrottle`, `FinancialMutationThrottle`
- heavy exports are async through `AsyncReportRequest` and Celery
- target API response time: `<= 2s` at p95

Security and governance:
- encrypted database backups
- secrets via environment variables
- audit retention minimum seven years
- business-critical coverage target `>= 80%`
- approved financial evidence must be archived with retention policy
- transient duplicate or cache files may be purged after policy TTL
- required governance docs:
  - ISMS scope and risk register
  - security controls matrix
  - data governance standard
  - DR/BCP runbook
  - release governance standard
  - PRD baseline

---

## Change Acceptance Standard

Any V12-ready change must satisfy all of the following before being described as complete:
- code path exists and is mode-aware where applicable
- doctrine is updated
- relevant skills are updated
- fiscal lifecycle changes update route/operator doctrine and any linked maintenance command references
- release evidence or blocker note exists
- mode separation remains intact
- sector governance and attachment policy remain policy-aware
- no verified axis regresses
- any renewed `100/100` claim after code or evidence changes must be re-proven through `verify_axis_complete_v21`


## V12 Closure Additions
- Approval requests must preserve `current_stage`, `total_stages`, `final_required_role`, and `approval_history`.
- Self-approval remains forbidden by default. The only governed exception is creator self-approval of a `critical variance` through `approve_variance` when `FarmSettings.allow_creator_self_variance_approval=true`; this exception never permits creator self-approval of the final daily log and must leave append-only audit evidence. Superuser break-glass remains a separate emergency control.
- The same actor must not clear more than one approval stage on the same request.
- Remote weekly sector review for eligible `SMALL` farms must be trackable via `RemoteReviewLog`.
- Attachment lifecycle must include file signature validation, archive tier transition, and transient purge commands.


## V13 Phase-1 Gap Closure Addendum
- قطاع STRICT صار يملك تقارير work queues وSLA escalation للموافقات عبر أوامر إدارة.
- تم تشديد دور المدير المالي للمزرعة داخل دورات Petty Cash / Supplier Settlement / Fiscal Close.
- المزرعة البعيدة الصغيرة أصبحت قابلة للحجب في بعض إجراءات STRICT عند تأخر المراجعة القطاعية.
- تمت إضافة legal hold / restore commands وتحسين سياسات رفع الملفات وفحص التوقيع والبصمة ومنع التكرار المؤقت.


## V14 Phase-2 Operationalization Addendum
- Approval requests now expose queue-aware metadata (`queue_snapshot`, `stage_chain`, SLA posture, and user-approvability) for UI inboxes and dashboards.
- The repository must ship a governed maintenance cycle command (`run_governance_maintenance_cycle`) that orchestrates attachment scanning, approval escalation, remote-review enforcement, archive, and purge tasks.
- Attachment lifecycle must preserve `archive_backend`, `archive_key`, `scanned_at`, `quarantined_at`, and `restored_at` once phase-2 metadata exists.
- Pending uploads must be scanned before they are treated as trustworthy evidence; quarantine outcomes must remain auditable.
- PRD, doctrine, and skills must describe the phase-2 operationalization, not just the abstract policy.


## V20 hardening and forensic controls
- Remote-site SMALL farms now record append-only sector-review escalations when weekly review windows lapse.
- Attachment lifecycle is append-only at the event level; scan, quarantine, authoritative marking, legal hold, archive, restore, and purge must leave forensic evidence.
- STRICT farms may require clean scans before documentary evidence is accepted.
- Any future claim above 95/100 must include runtime smoke, Django checks, and test execution evidence, not documentation alone.


## V21 Runtime and Forensic Closure
- V21 raises production readiness through a governed runtime probe, stronger attachment scanning hooks, and explicit role workbench attention counts.
- Do not claim runtime completeness unless `manage.py check`, migrations, targeted backend tests, and smoke commands run successfully on a provisioned stack.

## V21 Final Production Release Addendum (2026-03-26)
- Live `100/100` claims are authoritative only when the latest canonical `verify_axis_complete_v21` summary reports `overall_status=PASS` and `axis_overall_status=PASS`.
- Historical reports, handoff packs, and skill files remain traceability aids; they must not be cited above the latest canonical evidence.
- Repository hygiene or cleanup work does not become score proof by itself; any future score claim must be re-proven through canonical evidence.

## V22 YECO UX/UI Extensibility Addendum (2026-04-14)
- Currency control is strictly enforced at the UI boundary: Budget/Plan generation interfaces must exclusively lock to the default operating currency (`YER`), rejecting rendering of foreign options (`USD`, `SAR`).
- Material units of measure (UOM) must act predictably: generic materials selected via dropdowns must embed their UOM, preventing ambiguous unit logging. Budgets/plans auto-translate 'materials' categories to explicit standard measures (`kg` or `liter`) rather than generic `lot`.
- Material catalog links (`CropMaterials`) must distinctly manage `Crop` assignment arrays independently of base `Item` additions to guarantee field lookup integrity.
- **Offline Purge Governance (2026-04-17)**: Configurable retention policies for lookup cache, synced drafts, and dead-letter items are mandatory. Media purge and forensic local auditing must be available as optional governance toggles.
- **Temporal Enforcement**: Crop plan templates must enforce strictly sequenced activity windows to prevent chronological drift in field operations.

---

## V23 Sovereign Mobile Instrument Addendum (2026-04-18)

The AgriAsset Mobile Field App is formally elevated to a **Sovereign Field Instrument (V21.5-FINAL)**. It operates as a first-class evidence collection agent within the YECO ecosystem.

### Core Mobile Protocols
1. **Governed Inbox Logic (Axis 28)**: Navigation is workload-driven through role-based lanes (Pending, Returned, Drafts).
2. **AI Evidence Hardening (Axis 29)**: All field photos must undergo an automated 'Auto-Clarity' pass (AI brightness/contrast) to ensure forensic legibility.
3. **Forensic Local Vault (Axis 23)**: Mobile agents must maintain a local archaeological gallery with 7-day retention of high-res originals and metadata even after successful synchronization.
4. **GIS Stock Reconciliation (Axis 26)**: Field supervisors are empowered to perform physical tree counts and synchronize 'Biological Asset' balances locally.
5. **Simple-Mode Visibility (Axis 22)**: Storekeepers and Managers have role-specific dashboard cards for local inventory visibility and analytical field ratios (Achievement/Worker).
6. **Incremental Sync (Axis 20)**: Mobile agents must exclusively use delta-sync protocol to minimize bandwidth footprint in Northern Yemen's constrained radio environments.
7. **Attachment Class Discipline**: Field artifacts are tagged as `OPERATIONAL_EVIDENCE` by default and must carry forensic watermarks (Timestamp, GPS if enabled, Operator ID).
---

## V24 Shabwah Genesis and Finality (2026-04-18)

The AgriAsset Sovereign GRP has achieved its final 'Genesis' state through the successful execution of the **Shabwah Farm End-to-End Simulation**.

### Finality Certification (100/100)
1. **End-to-End Integrity (Axis 21)**: Full validation of the Shabwah Farm simulation across all biological and financial nodes.
2. **Mass Writeoff Sovereignty (Axis 18)**: Simulation of a mass casualty event (frost damage) successfully recorded and audit-trailed without manual correction.
3. **Dual-Mode Maturity**: SIMPLE and STRICT modes are fully synchronized over the same backend truth chain.
4. **Forensic Evidence Layer**: All transactions carry the required forensic metadata (GPS, Operators, Idempotency).
5. **Sovereign Instrument Ready**: Mobile and Desktop clients are formally certified for field deployment in Northern Yemen.

**SYSTEM STATUS: GENESIS COMPLETE. 100/100 Operational Maturity Verified.**
