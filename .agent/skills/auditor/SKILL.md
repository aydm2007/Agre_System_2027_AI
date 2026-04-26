---
name: auditor
description: Forensic scoring and chain-of-custody rules for AgriAsset mutations, workflows, V21 sector approvals, smart-card-stack canon, and evidence lifecycle.
---

# Auditor

Role: forensic tracer and scoring authority.
Scoring rule: every axis or workflow is `PASS`, `BLOCKED`, or `FAIL` based on evidence, not confidence.

## 1. Chain of Custody
- Every sensitive mutation must identify actor, timestamp, farm scope, reason, and before/after meaning.
- `AuditLog` and `FinancialLedger` are immutable records.
- `CRITICAL` variance requires approval trace before final posting.
- `DailyLog` tree shrink and `BiologicalAssetTransaction` write-offs are separate lanes and must remain separate in evidence.
- Mass casualty write-offs require explicit authorization and IAS 41 impairment trace.
- Attachment purge or archive actions must be auditable when evidence policies apply.

## 2. Workflow Scorecards
### Daily Execution Smart Card Stack
Pass only when evidence proves:
- `CropPlan -> DailyLog -> Activity -> Smart Card Stack -> Control -> Variance -> Ledger`
- the smart card stack is read-side only
- `smart_card_stack` is the canonical contract and is derived from `Activity.task_contract_snapshot` first
- legacy fields such as `daily_achievement`, `control_metrics`, `variance_metrics`, `ledger_metrics`, and `health_flags` remain compatibility-only, not the primary contract
- frontend review should assume stack-first rendering; legacy smart-card fields should appear only in explicit fallback scenarios
- routine tree shrink remains distinct from Axis 18
- the workflow is proven without QR dependency

### Petty Cash
Pass only when evidence proves:
- request and settlement posture exists
- cash disbursement is linked to balancing and liability trace
- `SIMPLE` stays control-focused
- `STRICT` exposes disbursement and settlement controls

### Receipts and Deposit
Pass only when evidence proves:
- receipt and deposit posture use the same truth in both modes
- `SIMPLE` shows collection posture and anomalies
- `STRICT` shows treasury and deposit trace

### Supplier Settlement
Pass only when evidence proves:
- payable source is valid
- approval and payment state are explicit
- partial and full settlement are distinguishable
- reconciliation state is surfaced
- `SIMPLE` remains summary/control focused
- `STRICT` exposes review, payment, and posting trace

### Contract Operations
Pass only when evidence proves:
- sharecropping, touring, and rental posture are unified
- touring is assessment-only and linked to production truth
- `SIMPLE` shows readiness, delay, and variance without full ERP clutter
- `STRICT` shows settlement, receipt, rent, and reconciliation posture
- financial vs physical sharecropping mode is preserved
- planned workflows are not mislabeled implemented

### Fixed Assets
Pass only when evidence proves:
- one fixed-asset register serves both modes
- `SIMPLE` shows tracking, health, and summarized value posture
- `STRICT` shows capitalization posture, book value, and depreciation trace
- the dashboard is read-side only and does not bypass ledger rules
- fixed assets are backed by governed action evidence, runtime snapshot evidence, and mode-aware API tests

### Fuel Reconciliation
Pass only when evidence proves:
- one fuel truth serves both modes
- `SIMPLE` shows machine or tank posture, expected vs actual fuel, and anomaly state without ERP clutter
- `STRICT` shows reconciliation posture and governed trace over the same rows
- the dashboard is read-side only
- fuel flags such as missing calibration, missing benchmark, warning, and critical variance are surfaced
- fuel reconciliation is backed by governed posting evidence, runtime snapshot evidence, and mode-aware API tests

### Sector Approval Chain
Pass only when evidence proves:
- sector accountant, sector reviewer, sector chief accountant, sector finance director, and sector director responsibilities are not falsely collapsed
- threshold-based routing is explicit where required
- `SIMPLE` does not expose the full chain to ordinary users by default
- hard-close evidence remains sector-owned

### Attachment Lifecycle
Pass only when evidence proves:
- attachment classes are explicit
- transient vs authoritative evidence is distinguished
- final approved financial evidence is archived and retained, not treated like cache
- clean, quarantine, archive, legal hold, restore, and purge-eligible scenarios are traceable independently
- purge or archive actions are auditable

## 3. Review Checklist
For reviews, verify:
- actor identity is present
- `farm_id` scope is preserved
- `IdempotencyRecord` linkage exists where required
- ledger rows were not updated or deleted
- approval continuity exists for `CRITICAL` variance
- ordinary tree death is not confused with mass casualty impairment
- workflow evidence is backed by tests or command output, not screenshots alone
- doctrine and skills reflect the implemented workflow
- mode boundaries are preserved
- small-farm compensating controls are explicit where the same officer holds multiple local finance hats

## 4. Required Evidence
Use [docs/doctrine/VERIFICATION_COMMANDS_V2.md](../../../docs/doctrine/VERIFICATION_COMMANDS_V2.md) as the current readable command reference.

Require:
- general release gate
- workflow-specific gate for the changed workflow
- `check_compliance_docs.py` when doctrine, skills, or PRD change
- treat `python backend/manage.py verify_axis_complete_v21` as the canonical final-score gate when the requested scope reaches `100/100`

## 5. Output Rules
When reporting findings:
- list findings first, ordered by severity
- include exact file references
- state what is proven, what failed, and what was blocked
- do not award `100/100` unless every mandatory evidence item for the requested scope is green and the doctrine layer is current
- for repo-wide `100/100`, require `verify_axis_complete_v21` with `overall_status=PASS` and `axis_overall_status=PASS`


## V15 Phase-2 Focus
- queue snapshots, approval histories, and maintenance-cycle outputs are auditable evidence
- quarantined attachments and restore operations must remain traceable


## V15 delta
- V15 forensic authority chain.
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
- **PostgreSQL is the sole permitted database engine for forensic scoring and compliance evidence.**
- SQLite is strictly banned for governance validation, test runs, production, and schema-drift checks.
- All audit trail integrity checks, `AuditLog` and `FinancialLedger` immutability proofs, and RLS tenant isolation verification must be evaluated against live PostgreSQL.
- Test evidence produced under SQLite is not admissible for compliance scoring — mark it `BLOCKED`.
- When scoring runtime readiness axes (11-15), require PostgreSQL connection proof as a prerequisite.

## V23 Sovereign Mobile Field Audit (Axis 21)
Pass only when evidence proves:
- **Forensic Handshake**: Mobile-generated `uuid` and `idempotency_key` are validated in `OfflineDailyLogReplayViewSet`.
- **Sync Integrity**: Out-of-order `client_seq` replay is blocked or quarantined in `SyncConflictDLQ`.
- **Evidence Formatting (Axis 29)**: `AttachmentSanitizer` pass is mandatory for legibility (Auto-Clarity).
- **Workload Compliance (Axis 28)**: Governed Inbox lanes correctly partition 'Pending' and 'Returned' tasks.
- **Artifact Retention (Axis 23)**: `SecureStorageService` maintains high-res audit originals for 7 days.
