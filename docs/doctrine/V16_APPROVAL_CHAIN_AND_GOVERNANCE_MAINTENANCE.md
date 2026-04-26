# V16 Approval Chain and Governance Maintenance

## Scope
V16 deepens the governed approval surface without claiming full runtime closure.

## What changed
- Approval request creation now builds chains with awareness of `FarmSettings.approval_profile`.
- Queue snapshots and maintenance summary expose pending, overdue, strict-finance, and remote-review posture.
- A unified command `run_governance_maintenance` now runs: overdue approval escalation, attachment scan/archive/purge queues, and remote-review due reporting.
- Sharecropping receipt posting now follows `require_profiled_posting_authority`, aligning it with fixed assets, fuel reconciliation, petty cash, and contract payment posting.

## Remaining limits
- This is still not a full workflow engine with persisted queue ownership, delegation, SLA timers, or scheduled jobs.
- Runtime proof and full Django/frontend test evidence remain outside this repository-only uplift.
