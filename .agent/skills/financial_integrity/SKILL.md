---
name: financial_integrity
description: CFO-grade rules for ledger safety, farm-vs-sector finance governance, settlement trace, evidence lifecycle, and evidence-gated readiness.
---

# Financial Integrity

Role: guardian of the ledger, costing engine, farm finance governance, and finance-facing workflows.
Status: aligned with the 18-axis protocol in [AGENTS.md](../../../AGENTS.md).

## 1. Money Rules
- `FinancialLedger` is append-only. Corrections use reversal entries in an open period.
- New ledger rows must carry `farm_id`, `cost_center`, and `crop_plan` whenever the business object supports them.
- `Decimal` is mandatory. `float()` in finance or inventory code is a compliance failure.
- Financial mutations require `X-Idempotency-Key` and cache-replay semantics.
- Closed fiscal history is immutable.

## 2. Farm and Sector Finance Governance
### Farm level
- `SMALL`: local accountant may act as local chief accountant and acting farm finance manager only under explicit policy and compensating controls.
- `MEDIUM/LARGE`: a dedicated `المدير المالي للمزرعة` is required.
- Farm finance leadership owns local budgeting, local treasury posture, soft-close readiness, and local documentation quality.
- `رئيس حسابات المزرعة` is the local accounting-review and soft-close-readiness role; it does not replace `رئيس حسابات القطاع`.

### Sector level
- sector accountant: first structured sector-side review
- sector reviewer: second-line review and maker-checker challenge
- sector chief accountant: accounting sign-off and reconciliation readiness
- sector finance director: final financial approval and hard-close authority
- sector director: business/executive final approval when policy requires it

## 3. Daily Execution Financial Contract
- `Activity` is the posting source for daily execution; the smart card is not.
- The smart card is a financial and control read model only.
- Daily execution must remain single-plan: one `DailyLog`, one `CropPlan`, one costing lane.
- Costing is computed on the backend from technical inputs only.
- If an activity is edited and economic meaning changes:
  - reverse prior effect
  - post corrected effect
  - preserve the audit trail
- Negative tree deltas in `DailyLog` are descriptive operational evidence and may trigger variance or reconciliation. They are not a substitute for impairment workflow.
- Mass tree losses route to Axis 18 write-off flow with explicit authorization and IAS 41 traceability.

## 4. Dual-Mode Finance Contract
- `SIMPLE` may reduce finance visibility, but it must not reduce backend truth.
- `STRICT` exposes fuller treasury, payable, settlement, reconciliation, and sector approval controls over the same truth.
- Smart cards remain read-side only in both modes.
- `cost_visibility` governs what the UI may reveal, not what the backend must record.
- Frontend finance-facing surfaces in `SIMPLE` must stay posture-first:
  - no explicit ledger authoring
  - no settlement posting buttons
  - no raw ledger absolutes beyond policy
- Refuse any design that treats simple mode as a place to hide broken finance truth.

## 5. Contract Operations Finance Contract
- Touring is assessment-only and must anchor to production truth.
- Sharecropping must preserve physical-share vs financial-settlement policy behavior.
- Contract settlement, receipts, and reconciliation are strict-mode finance surfaces.
- Contract operations must not inject technical crop execution tasks as if they were agronomy truth.

## 6. Implemented Finance Workflows
- Petty Cash
  - `SIMPLE`: request state, settlement-due posture, summarized values
  - `STRICT`: request, approval, disbursement, settlement, balancing
- Receipts and Deposit
  - `SIMPLE`: collection and anomaly posture
  - `STRICT`: treasury and deposit trace
- Supplier Settlement
  - `SIMPLE`: payable posture, delay, approval summary
  - `STRICT`: review, approval, payment, reconciliation, posting trace
- Contract Operations
  - `SIMPLE`: contract posture, expected share/rent, delay, touring status, summarized risk
  - `STRICT`: settlement, receipt trace, rental payment trace, reconciliation posture, approval chain
- Fixed Assets
  - `SIMPLE`: asset register, depreciation health, summarized visibility
  - `STRICT`: capitalization posture, book value, depreciation trace, fixed-asset control surface
- Fuel Reconciliation
  - `SIMPLE`: expected vs actual fuel, alert state, anomaly posture, summarized values
  - `STRICT`: reconciliation posture, treasury or inventory trace visibility, governed detail

## 6.1 Role-to-Workflow Gate Expectations
- `رئيس حسابات المزرعة`: local accounting review, accounting-pack quality, and soft-close readiness only.
- `المدير المالي للمزرعة`: local finance gate for governed strict workflows at the farm level where policy requires it.
- `رئيس حسابات القطاع`: accounting sign-off, reconciliation sign-off, and sector close-readiness gate.
- `المدير المالي لقطاع المزارع`: sector-final financial approval for governed thresholds, exceptions, and `strict_finance` final posting actions.
- Petty cash, supplier settlement, fixed assets, fuel reconciliation, contract payment posting, and fiscal close must preserve this distinction; no workflow may silently collapse farm-local review into sector-final authority.

## 7. Biological and Cash Controls
- `JUVENILE` or `RENEWING` cohorts capitalize eligible costs.
- `PRODUCTIVE` cohorts expense eligible daily costs.
- Casual labor batches paid through cash must create interim `WIP Labor Liability` and require petty-cash settlement.
- Zakat and solar depreciation remain toggle-aware but must preserve strict ledger integrity when enabled.

## 8. Evidence and Attachment Policy
- Draft or duplicate working files may be transient and TTL-managed.
- Approved authoritative finance records must be archived and retained.
- Purging hot-storage copies must not destroy the authoritative record.
- Attachment metadata should support evidence class, retention class, archive state, approval time, and hash where feasible.

## 9. Release Evidence
Use [docs/doctrine/VERIFICATION_COMMANDS_V2.md](../../../docs/doctrine/VERIFICATION_COMMANDS_V2.md) as the readable current release-gate reference.

When finance, daily execution, variance, biological assets, settlement workflows, attachment lifecycle, or role governance change, require:
- general finance release gate
- daily execution smart card gate when DailyLog or smart-card integration changes
- petty cash gate
- receipts/deposit gate
- supplier settlement gate
- contract operations gate
- fixed assets gate
- fuel reconciliation gate
- `check_compliance_docs.py` for doctrine/skills/PRD alignment

Treat missing evidence as `BLOCKED`, not complete.

## 10. Refusal Triggers
Refuse designs that:
- let the UI write ledger rows directly
- overwrite existing ledger meaning instead of reversing
- mix multiple crop plans into one daily costing document
- bypass petty-cash settlement for cash labor liabilities
- downgrade mass casualty accounting into a routine Daily Log correction
- treat fuel reconciliation as fully complete before wider workflow evidence exists
- collapse sector approval into one role while claiming global-grade finance governance
- rapidly delete final approved financial evidence to save storage


## V15 Phase-2 Focus
- finance evidence attachments should not be treated as trusted until scan status is passed or formally quarantined
- approval workload and overdue posture should be visible to finance leadership


## V15 delta
- V15 profiled posting authority.
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
- **PostgreSQL is the sole permitted database engine for all financial integrity checks.** SQLite is strictly banned.
- Ledger safety, decimal enforcement, idempotency verification, and RLS tenant isolation must be validated against a live PostgreSQL instance.
- `Decimal` column types and PostgreSQL `NUMERIC` precision must match across Django models and the live schema.
- Financial cycle tests (petty cash, supplier settlement, receipts, fixed assets, fuel reconciliation) must execute against PostgreSQL — never SQLite.
- Schema drift checks (`makemigrations --check --dry-run`) must run against the PostgreSQL backend to capture trigger and constraint behavior that SQLite cannot reproduce.
- On Windows, preload backend PostgreSQL credentials through `scripts/windows/Resolve-BackendDbEnv.ps1` before any financial verification command.
## V21.5 Sovereign Finality (2026-04-18)
- Axis 21 (Finality): The GRP is formally certified for production through the **Shabwah Farm End-to-End simulation**.
- Ledger Hardening: Financial transactions in the Shabwah simulation (capitalization, payroll, writeoffs) satisfy append-only forensic standards.
- 100/100 Score: Score is authoritative when `verify_axis_complete_v21` and 'Shabwah Genesis' evidence align.
- GENESIS COMPLETE: The financial engine is production-ready.
