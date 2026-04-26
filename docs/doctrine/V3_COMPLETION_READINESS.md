# V3 Completion Readiness

## What changed in the downloadable V3 candidate

- Auth user/group writes were moved behind explicit service owners in `accounts/services.py`.
- `accounts/api_auth.py` no longer performs direct user, group, or permission mutations inline.
- `finance/api_expenses.py` now delegates soft-delete to `ActualExpenseService.delete_expense(...)`.
- Fixed-assets and fuel-reconciliation dashboards now resolve their read models through dedicated services:
  - `core/services/fixed_asset_workflow_service.py`
  - `core/services/fuel_reconciliation_service.py`
- Documentary-cycle traceability is now explicit in `docs/doctrine/DOCX_CODE_TRACEABILITY_MATRIX_V3.md`.
- Runtime/bootstrap expectations are documented and statically checkable via `check_bootstrap_contract.py`.

## Static evidence available now

```bash
python backend/scripts/check_no_float_mutations.py
python backend/scripts/check_idempotency_actions.py
python scripts/check_farm_scope_guards.py
python scripts/verification/check_no_bare_exceptions.py
python scripts/verification/check_service_layer_writes.py
python scripts/verification/check_accounts_service_layer_writes.py
python scripts/verification/check_auth_service_layer_writes.py
python scripts/verification/check_bootstrap_contract.py
python scripts/verification/check_docx_traceability.py
```

## Still required for a provable 100/100

The repository remains evidence-gated. A fully proven `100/100` still requires a live environment with:

- Django + DRF installed
- PostgreSQL connectivity and migration access
- frontend dependencies installed
- browser drivers for Playwright
- runtime proof for schema parity, zombie/ghost checks, and end-to-end workflows

Until that environment is available and the runtime commands pass, V3 is stronger structurally and doctrinally but still not honestly claimable as a proven `100/100`.
