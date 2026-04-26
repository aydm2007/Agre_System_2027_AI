# Phase 5 — Period Close & Audit Enforcement

**Scope:** Enforce fiscal period locks for financial mutations and log approvals, ensuring hard-closed periods are immutable.

## What Changed
- ActualExpense create/update now validates the fiscal period is open before posting.
- DailyLog approval enforces fiscal period openness before financial locking.

## Workflow Rules
- **Open only:** Mutations dated inside soft/hard-closed periods are rejected.
- **Hard-close immutable:** Corrections must be posted as reversal entries in an open period.

## Yemen Context Alignment
- Ensures auditability and deterministic financial behavior under weak-network retries.
- Keeps farm periods legally independent and immutable after close.
