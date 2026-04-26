# Farm Scope Exceptions Policy

## Purpose
This document governs exceptions to automatic farm-scope guard enforcement.
By default, mutable business endpoints must enforce tenant/farm scope.

## Source of Truth
- Machine-readable list: `scripts/farm_scope_exceptions.json`
- Enforced by: `scripts/check_farm_scope_guards.py`

## Exception Rules
- Every exempted ViewSet class must have:
  - `reason` (non-empty)
  - `owner` (team/domain accountable)
  - `review_due` (ISO date `YYYY-MM-DD`)
- Exemptions are allowed only for:
  - framework/base classes
  - global authentication/authorization administration
  - approved master/reference data endpoints
  - explicitly documented orchestration endpoints with separate access controls

## Change Process
1. Add/update entry in `scripts/farm_scope_exceptions.json`.
2. Include clear reason and owner.
3. Run:
   - `python scripts/check_farm_scope_guards.py`
4. Submit change with security/architecture review note.

## Expiry Enforcement
- If `review_due` is in the past, CI must fail.
- Any expired exception must be reviewed, renewed, or removed before merge.

## Prohibited
- Temporary or blank reasons.
- Exempting tenant business mutation endpoints to bypass proper farm scoping.
