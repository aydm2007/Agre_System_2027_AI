# Phase 2 — Idempotency Enforcement Hardening

**Scope:** Enforce `X-Idempotency-Key` on mutation endpoints and make duplicate retries deterministic across create/update/delete paths.

## What Changed
- **Global mutation enforcement:** `IdempotentCreateMixin` now enforces idempotency for `create`, `update`, `partial_update`, and `destroy`, rejecting missing keys with `400` and replaying cached responses for duplicate keys.
- **Replay for deletes:** Cached responses now support `204 No Content` to keep retries deterministic.
- **Broader coverage:** All `AuditedModelViewSet` subclasses inherit idempotency enforcement automatically, and HR viewsets now use the mixin for mutation routes.

## Coverage Notes
- **Core CRUD:** Crop/Planning/Inventory/Settings/Logs now require idempotency headers on creates via `AuditedModelViewSet`.
- **HR:** Employee, EmploymentContract, and Timesheet endpoints now enforce idempotency on create/update/delete.
- **Financial & Sales:** Existing idempotency-enabled viewsets now also enforce idempotency on update/delete for deterministic retries.

## Follow-ups
- Validate API client behavior for any legacy integrations that may be missing idempotency headers.
- Add automated tests for duplicate request replay on update/delete flows.
