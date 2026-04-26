# Phase 4 — Variance Engine & Approval Controls

**Scope:** Enforce variance thresholds with warning/critical handling and approval workflow safeguards.

## What Changed
- Added variance thresholds (warning/critical) to `CostConfiguration` for per-farm control.
- Introduced DailyLog variance tracking fields and enforced variance checks during log approval.
- Added manager-only variance approval action for critical variances.

## Workflow Rules
- **Warning variance:** Requires a supervisor note before approval.
- **Critical variance:** Requires manager approval before log approval.

## Yemen Context Alignment
- Manual inputs remain the source of truth, but variance thresholds ensure oversight.
- Deterministic Decimal calculations prevent drift in weak-network retry scenarios.

## Follow-ups
- Add API/UI affordances to surface variance status and required actions to supervisors.
- Extend variance checks to other mutation flows where budgets apply.
