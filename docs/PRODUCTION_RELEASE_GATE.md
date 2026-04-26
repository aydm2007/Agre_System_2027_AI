# Production Release Gate (YECO Edition)

> [!IMPORTANT]
> Live release authority remains:
> - `docs/evidence/closure/latest/verify_release_gate_v21/summary.json`
> - `docs/evidence/closure/latest/verify_axis_complete_v21/summary.json`
>
> New-tenant supporting UAT authority for the current baseline:
> - `docs/evidence/uat/khameesiya/latest/summary.json`

This guide standardizes how teams run mandatory compliance checks before merging finance, inventory, period-close, or farm-scope changes.

## Why this exists

AgriAsset runs in weak-network environments with strict financial immutability and farm isolation requirements. A release is blocked if mandatory checks fail.

## One-command execution

From repository root:

```bash
python backend/manage.py verify_static_v21
```

For full verification including runtime probes:

```bash
python backend/manage.py verify_release_gate_v21
python backend/manage.py verify_axis_complete_v21
python backend/manage.py run_khameesiya_uat --artifact-root docs/evidence/uat/khameesiya/latest
```

Windows PowerShell fallback:

```powershell
& .\scripts\windows\Resolve-BackendDbEnv.ps1
python backend/manage.py verify_static_v21
python backend/manage.py verify_release_gate_v21
python backend/manage.py verify_axis_complete_v21
python backend/manage.py run_khameesiya_uat --artifact-root docs/evidence/uat/khameesiya/latest
```

## What the verification script runs

`python backend/manage.py verify_release_gate_v21` executes the canonical release suite:

1. Static policy and reference checks:
   - `check_bootstrap_contract.py`
   - `verify_postgres_foundation_contract.py`
   - `check_no_bare_exceptions.py`
   - `check_docx_traceability.py`
   - `verify_release_hygiene.py`
   - `check_no_float_mutations.py`
   - `check_idempotency_actions.py`
   - `check_farm_scope_guards.py`
   - `check_service_layer_writes.py`
   - `check_compliance_docs.py`
   - `backend/scripts/float_guard.py --strict`
2. Targeted PostgreSQL backend suites for:
   - smart-card and SIMPLE/STRICT separation
   - approvals, reopen, and override
   - attachments and runtime contracts
   - supplier settlement and profiled posting authority
   - contract operations, fixed assets, fuel reconciliation, and petty cash
3. Frontend gates:
   - `npm --prefix frontend run lint`
   - focused `vitest` suites for smart cards, supplier settlement, contract operations, fixed assets, fuel, petty cash, and receipts
   - `npm --prefix frontend run build`
4. Runtime closure evidence:
   - `python backend/manage.py check --deploy`
   - `python backend/manage.py seed_runtime_governance_evidence`
   - `python backend/manage.py showmigrations --plan`
   - `python backend/manage.py migrate --plan`
   - `python backend/manage.py runtime_probe_v21`
   - `python backend/manage.py release_readiness_snapshot`
   - `python backend/manage.py scan_pending_attachments`
   - `python backend/manage.py report_due_remote_reviews`
   - `python backend/manage.py dispatch_outbox`
   - `python backend/manage.py retry_dead_letters`
   - `python backend/manage.py purge_dispatched_outbox --dry-run`
5. New-tenant dual-mode UAT proof:
   - `python backend/manage.py run_khameesiya_uat --artifact-root docs/evidence/uat/khameesiya/latest`
   - validates `SIMPLE` and `STRICT` over the same tenant truth chain
   - validates tomato seasonal execution, mango/banana perennial execution, inventory, governed finance, sales, contract operations, attachments, and governance workbench evidence

## Canonical RLS tables

- `core_dailylog`
- `core_activity`
- `core_financialledger`
- `core_treasurytransaction`
- `accounts_roledelegation`

## Usage notes

- Run the script before creating a production PR.
- Treat `run_khameesiya_uat` as mandatory for the current Gold Freeze baseline, not as a substitute for canonical closure gates.
- On Windows, preload backend DB credentials with `scripts/windows/Resolve-BackendDbEnv.ps1` when running Django commands manually from the repository root.
- The script validates DB environment configuration (`DB_NAME`, `DB_USER`, `DB_PASSWORD`) before Django commands to avoid ambiguous startup failures.
- Legacy wrappers `make verify-static`, `make verify-release-gate`, `scripts/verify_static.ps1`, `scripts/verify_release_gate.ps1`, and `scripts/closure/run_closure_evidence.sh` now delegate to the canonical Django commands.
- Use `--skip-runtime-probes` only for fast local iteration.
- Runtime probes must pass in CI/staging before release approval.

## Failure policy

Any failed check is a hard stop for release and must be remediated before merge.

## Non-Functional Evidence Bundle (Mandatory)

- `docs/compliance/ISMS_SCOPE_AND_RISK_REGISTER.md`
- `docs/compliance/SECURITY_CONTROLS_MATRIX.md`
- `docs/compliance/DR_BCP_RUNBOOK.md`
- `docs/compliance/DATA_GOVERNANCE_STANDARD.md`
- `docs/compliance/RELEASE_GOVERNANCE_STANDARD.md`
- `docs/reports/GLOBAL_BASELINE_GAP_REGISTER.md`
- `docs/reports/GLOBAL_READINESS_EVIDENCE_<YYYY-MM-DD>.md`
- `docs/reports/DR_DRILL_<YYYY-MM-DD>.md`
