# AgriAsset Agents Protocol
## Version: 4.0.0 (2026-03-16)

> [!IMPORTANT]
> SYSTEM STATUS: EVIDENCE-GATED. `100/100` requires verified pass across 18 axes.
> Strict no-regression mode is active. Any change that lowers a verified axis must be rejected.

> [!NOTE]
> CHANGELOG v4.1.0: V19 strengthened farm-finance vs sector-director visibility in the approval workbench, added explicit remote-review escalation ownership, and hardened uploads against hidden executable double-extensions and oversized container payloads.

---

## Identity and Scope
- System: AgriAsset (YECO Edition)
- Owner: Yemeni Economic Corporation - Agriculture Sector
- Model: Hybrid Government Resource Planning (GRP)
- Context: Northern Yemen, weak internet, manual entry as source of truth
- Scope: entire repository; deeper `AGENTS.md` files override inside their subtrees
- Terminology: [docs/GLOSSARY.md](docs/GLOSSARY.md)

---

## Core Operating Rules
1. Service layer only: views and tasks never write transactional rows directly.
2. Decimal only: `float()` is banned in finance and inventory logic.
3. Strict UI validation: non-delta numeric inputs must enforce non-negative input.
4. Idempotency V2: all financial `POST/PATCH` operations require `X-Idempotency-Key`.
5. Append-only ledger: no `UPDATE` or `DELETE` on `FinancialLedger`.
6. Tenant isolation: every transactional row carries `farm_id`; scope must hold in Python and PostgreSQL.
7. RTL first: React/Vite layouts must support Arabic RTL and dark mode.
8. Explicit error handling only: use `ValidationError`, `PermissionDenied`, or concrete DB exceptions. Never swallow bare `except Exception`.
9. Surra law: labor costing is daily-rate based, not hourly payroll.
10. Analytical purity: `FinancialLedger` rows require `cost_center` and `crop_plan` when the business object supports them.
11. Rejected logs must support reopening back to `DRAFT`.
12. Dual-mode ERP: `SIMPLE` hides explicit ledger authoring while backend posts shadow accounting; `STRICT` exposes full ERP controls.
13. Feature toggles such as Zakat, depreciation, sharecropping, petty cash, and attachment policy classes must be tenant-configurable and enforced in backend rules.
14. Simple-mode route breaches must emit `AuditLog`, not just redirect.
15. Simple-mode agronomy dashboards may expose burn-rate style ratios without leaking forbidden absolute finance values.
16. Strict single-crop costing: each `DailyLog` maps to exactly one `CropPlan`.
17. Petty cash settlement: cash labor batches must post interim `WIP Labor Liability` and settle against a voucher.
18. Mass exterminations: extraordinary tree deaths must use a dedicated `Mass Casualty Write-off` workflow linked to IAS 41 impairment.
19. Farm-size governance: `SMALL` farms may use a single local finance officer only under compensating controls; `MEDIUM/LARGE` farms require a dedicated farm finance manager.
20. Sector governance: sector approval is multi-level in `STRICT` and must not collapse into one overpowered role.
21. Contract operations doctrine: sharecropping, touring, and rent settlement are not technical crop execution; touring is assessment-only and anchored to harvest/production truth.
22. Attachment lifecycle doctrine: approved authoritative financial evidence is archived and retained, not quickly deleted; only transient duplicates, cache copies, and draft artifacts may expire on TTL.
23. `SIMPLE` is a technical agricultural control surface, not a diluted ERP authoring surface.
24. Profiled final posting authority: farms using `approval_profile=strict_finance` require sector-final authority for final financial posting actions in supplier settlement, petty cash disbursement/settlement, fixed assets, fuel reconciliation, and contract payment posting.
25. Admin convenience must not silently reopen full financial route trees in `SIMPLE`; finance route registration follows the effective mode contract.
26. Forensic approval timeline: every approval request in `STRICT` must leave stage-event evidence (`created`, `stage approved`, `final approved`, `rejected`, `auto escalated`) that can be queried independently from the mutable UI state.
27. Sector role workbench: `STRICT` governance must expose grouped workload visibility for sector accountant, reviewer, chief accountant, finance director, and sector director lanes.
28. Attachment intake hardening: PDF JavaScript/OpenAction markers and XLSX macro or zip-bomb patterns must be blocked or quarantined before evidence becomes authoritative.

---

## Daily Execution Smart Card Contract

Canonical path:
`CropPlan -> DailyLog -> Activity -> Smart Card -> Control -> Variance -> Ledger`

- `CropPlan` is the planning source of truth.
- `Activity` is the operational source of truth.
- The smart card inside `DailyLog` is read-side only. It must not create, mutate, or approve ledger rows directly.
- The smart card contract for this workflow is:
  - `plan_metrics`
  - `task_focus`
  - `daily_achievement`
  - `control_metrics`
  - `variance_metrics`
  - `ledger_metrics`
  - `health_flags`
- **Dynamic UX Mandate**: The frontend UI (`/crops/tasks`, `DailyLog`) MUST NOT use static checkboxes for task capabilities. The UI must dynamically render the exact Smart Cards dictated by the `task_contract` JSON returned by the backend, depending on the task's `archetype` (e.g., Seasonal vs Perennial).
- **Archetype Integration Policy**: Modules communicating with DailyLog (e.g., TreeCensus Launchpad) MUST pass strict `archetype` keys (e.g., `BIOLOGICAL_ADJUSTMENT`) instead of localized hardcoded task names. The target UI must resolve the task internally using the archetype to ensure localization safety and strict capability enforcement.
- This workflow does not depend on QR. Manual field entry is the required source of truth here.
- Costing is computed on the backend from technical inputs only.
- Activity edits must reconcile operational state and use reversal plus re-posting for financial corrections.
- Routine tree add/update/death may appear in daily execution:
  - positive delta: operational addition/reconciliation
  - negative delta: descriptive operational evidence that must generate variance and managerial trace
- Routine negative `tree_count_delta` must not be treated as a capital impairment shortcut.
- Extraordinary mass tree deaths must leave Daily Log correction flow and enter Axis 18 `Mass Casualty Write-off`.

---

## Dual-Mode Operating Contract

`FarmSettings` is the primary source of truth for operational mode and policy behavior at the farm level.

- `FarmSettings.mode` controls the effective user-facing contract per farm.
- `SystemSettings.strict_erp_mode` may remain as a legacy global override or bootstrap signal, but it is not the primary contract for new dual-mode workflows.
- `SIMPLE` means a technical agricultural control system:
  - plans
  - materials
  - `DailyLog`
  - smart cards
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
- Both modes share the same truth chain:
  - `CropPlan -> DailyLog -> Activity -> Smart Card -> Control -> Variance -> Ledger`
- Smart cards are read-side only in both modes.
- `SIMPLE` must preserve shadow accounting, auditability, and variance generation.
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
- Sector chain provides review, escalation, and final governed approval.

### `LARGE`
- Must have a dedicated `المدير المالي للمزرعة` plus stronger internal segregation.
- Treasury, settlement, and period-close evidence must be more explicit.
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

### Design restrictions
- Sector roles must not all collapse into a single overpowered finance role.
- Sector roles must not replace normal farm execution in ordinary daily work.
- `SIMPLE` should not expose the entire sector chain to ordinary field users.

---

## Operational Cycles by Mode

The following workflows are part of the V12 contract and must remain mode-aware:

- `Daily Execution Smart Card`
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

---

## Reference Integrity

`100/100` cannot be awarded when the reference layer is broken.

- Doctrine files must be readable, current, and aligned with implemented workflows.
- Release commands must match actual code paths and current tests.
- A workflow implemented in code but missing from doctrine or skills is a reference failure.
- If a release-gate script is blocked by write-locked output files or environment limitations, the condition is `BLOCKED` unless alternative documented evidence is explicitly recorded in the readiness report.
- Known debt must remain labeled as debt, not implied complete:
  - `lease_service.py` still requires direct cleanup even though rental workflow is operational through contract-operations aggregation
  - `fixed assets` is implemented as a mode-aware dashboard and depreciation/register surface, but full fixed-asset workflow evidence is still partial
  - `fuel reconciliation` is implemented as a mode-aware dashboard and release-gate surface, but workflow actions are still partial

---

## Doctrine References

| Doctrine | File | Scope |
|----------|------|-------|
| Financial Rules | [docs/doctrine/FINANCIAL_DOCTRINE.md](docs/doctrine/FINANCIAL_DOCTRINE.md) | Fund accounting, fiscal lifecycle, Zakat, IAS 41 |
| Hybrid Mode | [docs/doctrine/HYBRID_MODE_V2.md](docs/doctrine/HYBRID_MODE_V2.md) | current SIMPLE/STRICT behavior |
| V12 Governance and Mode Policy | [docs/doctrine/V12_GOVERNANCE_AND_MODE_POLICY.md](docs/doctrine/V12_GOVERNANCE_AND_MODE_POLICY.md) | V12 mode boundaries, farm-size governance, sector chain |
| V12 Sector Governance and Approvals | [docs/doctrine/V12_SECTOR_GOVERNANCE_AND_APPROVAL_CHAIN.md](docs/doctrine/V12_SECTOR_GOVERNANCE_AND_APPROVAL_CHAIN.md) | roles, thresholds, approval ladders |
| V12 Attachment Evidence Lifecycle | [docs/doctrine/V12_ATTACHMENT_EVIDENCE_LIFECYCLE.md](docs/doctrine/V12_ATTACHMENT_EVIDENCE_LIFECYCLE.md) | upload classes, retention, archive, purge |
| V14 Stage-2 Operationalization | [docs/doctrine/V14_STAGE2_OPERATIONALIZATION.md](docs/doctrine/V14_STAGE2_OPERATIONALIZATION.md) | queue-aware approvals, maintenance cycle, attachment runtime metadata |
| V15 Profiled Posting and Mode Enforcement | [docs/doctrine/V15_PROFILED_POSTING_AND_MODE_ENFORCEMENT.md](docs/doctrine/V15_PROFILED_POSTING_AND_MODE_ENFORCEMENT.md) | governed final posting authority and stricter SIMPLE/STRICT finance route enforcement |
| V16 Approval Chain and Governance Maintenance | [docs/doctrine/V16_APPROVAL_CHAIN_AND_GOVERNANCE_MAINTENANCE.md](docs/doctrine/V16_APPROVAL_CHAIN_AND_GOVERNANCE_MAINTENANCE.md) | profile-aware chains, unified maintenance command, remote review and attachment maintenance summary |
| Verification Commands | [docs/doctrine/VERIFICATION_COMMANDS_V2.md](docs/doctrine/VERIFICATION_COMMANDS_V2.md) | current release gate and blockers |
| Dual-Mode Operational Cycles | [docs/doctrine/DUAL_MODE_OPERATIONAL_CYCLES.md](docs/doctrine/DUAL_MODE_OPERATIONAL_CYCLES.md) | implemented and planned workflows by mode |
| Daily Execution Smart Card | [docs/doctrine/DAILY_EXECUTION_SMART_CARD.md](docs/doctrine/DAILY_EXECUTION_SMART_CARD.md) | non-QR execution, card contract, tree-loss separation |
| Documentary Cycle | [docs/doctrine/DOCUMENTARY_CYCLE.md](docs/doctrine/DOCUMENTARY_CYCLE.md) | end-to-end flow |
| Strict Completion Matrix | [docs/doctrine/STRICT_COMPLETION_MATRIX.md](docs/doctrine/STRICT_COMPLETION_MATRIX.md) | workflow-to-code traceability and mode alignment |
| Glossary | [docs/GLOSSARY.md](docs/GLOSSARY.md) | domain terms |
| Master PRD | [docs/prd/AGRIASSET_V14_MASTER_PRD_AR.md](docs/prd/AGRIASSET_V14_MASTER_PRD_AR.md) | product requirements baseline |

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
- `schema_sentinel` and `sql_sync` are deprecated aliases. Use `schema_guardian`.

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
- QR may remain optional for inventory or attendance outside this scenario, but it is not part of the Daily Execution Smart Card contract.
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
- release evidence or blocker note exists
- mode separation remains intact
- sector governance and attachment policy remain policy-aware
- no verified axis regresses


## V12 Closure Additions
- Approval requests must preserve `current_stage`, `total_stages`, `final_required_role`, and `approval_history`.
- Self-approval is forbidden except for superuser break-glass.
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
