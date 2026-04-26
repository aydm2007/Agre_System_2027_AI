# REMEDIATION REGISTER — V8

## Closed in V8
- Fixed Asset dashboard percentage calculation moved to `safe_percentage()` to satisfy the strong float gate.
- `integrations/api.py` no longer writes directly; governed writes move to `integrations/services.py`.
- Root `scripts/check_no_float_mutations.py` now delegates to the strong backend gate.
- V8 readiness evidence generated only from the strong float gate and V8 static gates.

## Still requires runtime evidence
- `manage.py check --deploy`
- `showmigrations`
- `migrate --plan`
- backend/frontend boot in provisioned environment
- E2E/Playwright and database-backed policy tests
