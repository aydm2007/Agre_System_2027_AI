# V44 Continuation Forensic Report — 2026-03-18

## Scope of this pass
- Agricultural path proof hardening
- Governance-by-role/tier proof hardening
- Financial integrity hardening
- Service-layer / outbox / observability contract closure
- Frontend install/build diagnostics

## Code fixes applied
1. `backend/smart_agri/core/api/viewsets/base.py`
   - `IdempotentCreateMixin.create()` now returns HTTP 405 for read-only resources instead of raising `AttributeError`.
2. `backend/smart_agri/core/api/reporting.py`
   - Imported `PermissionDenied` so cross-farm report rejection returns 403 instead of 500.
3. `backend/smart_agri/integration_hub/event_contracts.py`
   - Replaced fragile `super().__init__()` calls inside dataclass subclasses with explicit `IntegrationEvent.__init__(...)` to avoid runtime `TypeError` in outbox/domain-bridge events.
4. `backend/smart_agri/finance/services/ledger_balancing.py`
   - Exposed `FinancialLedger` at module scope with safe runtime fallback; improves patchability and forensic verifiability.
5. `backend/smart_agri/finance/services/ias41_revaluation.py`
   - Exposed `FinanceService` and `log_sensitive_mutation` at module scope with safe lazy fallback.
   - Preserved runtime behavior while making financial governance tests patchable and stable.
6. `backend/smart_agri/core/tests/test_financial_governance.py`
   - Added `pytestmark = pytest.mark.django_db` to align pytest execution with transaction-using IAS41 tests.
7. `backend/pytest.ini`
   - Added default pytest configuration targeting `smart_agri.test_settings_sqlite`.
8. `frontend/.npmrc`
   - Switched to `install-strategy=hoisted` and `bin-links=true` to reduce install fragility in ephemeral environments.

## Verification actually executed
### PASS
- `make verify-static`
- `python3 backend/manage.py check`
- `manage.py test` targeted suite: **62 tests PASS**
- `pytest -q smart_agri/core/tests/test_financial_governance.py -q` PASS (silent due `-q`)

### BLOCKED / ENVIRONMENTALLY UNSTABLE
- `npm ci` in this environment remains unstable/incomplete: the install completes only partially and does not reliably create an executable `.bin` toolchain.
- Therefore frontend `lint` / `build` / `vitest` could not be re-certified in this pass.
- PostgreSQL runtime proof remains blocked by absence of a live PostgreSQL service in this session.

## Strict interpretation
- Backend forensic assurance improved materially.
- Frontend production proof is **not** upgraded to PASS in this pass; it remains blocked by environment.
- PostgreSQL runtime proof remains blocked, not failed-by-code.
