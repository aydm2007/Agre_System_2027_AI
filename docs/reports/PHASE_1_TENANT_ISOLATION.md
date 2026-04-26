# Phase 1 — Tenant Isolation Hardening Report

## Summary
- Enforced farm scoping on all `AuditedModelViewSet` querysets when the model contains a `farm` foreign key.
- Added farm access checks during create/update for `AuditedModelViewSet` to prevent cross-farm writes.
- Preserved optional `farm`/`farm_id` query param filtering on farm-scoped models.

## Evidence
- Centralized farm scoping in `AuditedModelViewSet.get_queryset()` with `user_farm_ids` enforcement and explicit farm filter parameter support.
- Centralized farm access checks in `perform_create` / `perform_update` using `_ensure_user_has_farm_access`.

## Notes
- Models without a `farm` field are left unchanged by this baseline guard and should be reviewed individually for relationship-based farm scoping.
