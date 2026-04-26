# V21 Axis-Complete Verification

- command: `verify_axis_complete_v21`
- generated_at: `2026-04-18T23:19:53.232473-07:00`
- overall_status: `PASS`
- suite_dir: `C:\tools\workspace\AgriAsset_v44\docs\evidence\closure\20260418_230708\verify_axis_complete_v21`
- latest_dir: `C:\tools\workspace\AgriAsset_v44\docs\evidence\closure\latest\verify_axis_complete_v21`
- axis_overall_status: `PASS`

## Axis Summary

| # | Axis | Status | Code | Test | Gate | Runtime |
|---:|---|---|---|---|---|---|
| 1 | `Schema Parity` | `PASS` | `backend/smart_agri/core/migrations/, backend/smart_agri/finance/migrations/` | `backend/smart_agri/core/tests/test_schema_parity_runtime.py` | `python scripts/verification/detect_zombies.py ; python scripts/verification/detect_ghost_triggers.py` | `python backend/manage.py showmigrations --plan ; python backend/manage.py migrate --plan` |
| 2 | `Idempotency V2` | `PASS` | `backend idempotency middleware and financial mutation services` | `backend/smart_agri/core/tests/test_idempotency_middleware.py ; backend/smart_agri/finance/tests/test_fiscal_year_rollover_idempotency.py` | `python scripts/check_idempotency_actions.py` | `python backend/manage.py verify_release_gate_v21` |
| 3 | `Fiscal Lifecycle` | `PASS` | `backend/smart_agri/finance/services/fiscal_*` | `backend/smart_agri/finance/tests/test_fiscal_lifecycle.py ; backend/smart_agri/core/tests/test_fiscal_close_e2e.py` | `python scripts/check_fiscal_period_gates.py` | `python backend/manage.py release_readiness_snapshot` |
| 4 | `Fund Accounting` | `PASS` | `backend/smart_agri/core/services/financial_governance.py ; backend/smart_agri/finance/services/fiscal_fund_governance_service.py` | `backend/smart_agri/core/tests/test_financial_governance.py ; backend/smart_agri/finance/tests/test_financial_integrity_governance.py` | `python backend/manage.py verify_release_gate_v21` | `python backend/manage.py release_readiness_snapshot` |
| 5 | `Decimal and Surra` | `PASS` | `backend/smart_agri/core/services/costing.py ; finance/api_ledger_support.py` | `backend/smart_agri/core/tests/test_strict_decimals.py ; backend/smart_agri/core/tests/test_labor_estimation_api.py` | `python scripts/check_no_float_mutations.py ; python backend/scripts/float_guard.py --strict` | `python backend/manage.py verify_static_v21` |
| 6 | `Tenant Isolation` | `PASS` | `backend farm scope middleware and PostgreSQL RLS policies` | `backend/smart_agri/finance/tests/test_tenant_isolation.py ; backend/smart_agri/core/tests/test_rls_authorization.py` | `python scripts/check_farm_scope_guards.py` | `python backend/manage.py runtime_probe_v21` |
| 7 | `Auditability` | `PASS` | `backend/smart_agri/core/models/log.py::AuditLog ; append-only ledger flows` | `backend/smart_agri/core/tests/test_phase7_audit_append_only.py ; backend/smart_agri/core/tests/test_route_breach_middleware.py` | `python scripts/verification/check_service_layer_writes.py` | `python backend/manage.py verify_release_gate_v21` |
| 8 | `Variance and BOM` | `PASS` | `backend/smart_agri/core/services/schedule_variance_service.py ; DailyLog governance services` | `backend/smart_agri/core/tests/test_schedule_variance.py ; backend/smart_agri/core/tests/test_phase5_variance_workflow.py` | `python backend/manage.py verify_release_gate_v21` | `python backend/manage.py runtime_probe_v21` |
| 9 | `Sovereign and Zakat` | `PASS` | `backend/smart_agri/core/services/zakat_policy.py ; sovereign_zakat_service.py` | `backend/smart_agri/core/tests/test_phase6_zakat_solar.py ; backend/smart_agri/core/tests/test_zakat_policy_v2.py ; backend/smart_agri/sales/tests/test_sale_service.py` | `python backend/scripts/check_zakat_harvest_triggers.py ; python backend/scripts/check_solar_depreciation_logic.py` | `python backend/manage.py runtime_probe_v21` |
| 10 | `Farm Tiering` | `PASS` | `backend farm-size governance services and accounts delegation services` | `backend/smart_agri/core/tests/test_farm_size_governance.py ; backend/smart_agri/core/tests/test_v21_governance_comprehensive.py ; backend/smart_agri/accounts/tests/test_role_delegation.py` | `python scripts/verification/check_compliance_docs.py` | `python backend/manage.py run_governance_maintenance_cycle --dry-run` |
| 11 | `Biological Assets` | `PASS` | `backend tree inventory and impairment services` | `backend/smart_agri/core/tests/test_biological_asset_impairment.py ; backend/smart_agri/core/tests/test_tree_inventory.py` | `python backend/manage.py verify_release_gate_v21` | `python backend/manage.py release_readiness_snapshot` |
| 12 | `Harvest Compliance` | `PASS` | `backend harvest services and sales integration` | `backend/smart_agri/core/tests/test_harvest_products.py ; backend/smart_agri/core/tests/test_activity_requirements.py ; backend/smart_agri/core/tests/test_zakat_policy_v2.py` | `python backend/scripts/check_zakat_harvest_triggers.py` | `python backend/manage.py runtime_probe_v21` |
| 13 | `Seasonal Settlement` | `PASS` | `backend/smart_agri/core/services/seasonal_settlement_service.py` | `backend/smart_agri/core/tests/test_seasonal_settlement.py` | `python backend/manage.py verify_release_gate_v21` | `python backend/manage.py release_readiness_snapshot` |
| 14 | `Schedule Variance` | `PASS` | `backend/smart_agri/core/services/schedule_variance_service.py` | `backend/smart_agri/core/tests/test_schedule_variance.py` | `python backend/manage.py verify_release_gate_v21` | `npx --prefix frontend playwright test frontend/tests/e2e/daily-log-smart-card.spec.js` |
| 15 | `Sharecropping` | `PASS` | `backend sharecropping services and contract operations service` | `backend/smart_agri/core/tests/test_operational_contracts.py ; backend/smart_agri/core/tests/test_sharecropping_posting_service.py` | `python backend/manage.py verify_release_gate_v21` | `npx --prefix frontend playwright test frontend/tests/e2e/contract-operations.spec.js` |
| 16 | `Single-Crop Costing` | `PASS` | `backend activity cost snapshot and smart-card contract` | `backend/smart_agri/core/tests/test_activity_cost_snapshot_integrity.py ; backend/smart_agri/core/tests/test_v21_e2e_cycle.py` | `python scripts/check_no_float_mutations.py` | `npx --prefix frontend playwright test frontend/tests/e2e/daily-log-smart-card.spec.js` |
| 17 | `Petty Cash Settlement` | `PASS` | `backend/smart_agri/finance/services/petty_cash_service.py` | `backend/smart_agri/finance/tests/test_petty_cash_service.py ; backend/smart_agri/finance/tests/test_petty_cash_settlement.py` | `python backend/manage.py verify_release_gate_v21` | `python backend/manage.py release_readiness_snapshot` |
| 18 | `Mass Exterminations` | `PASS` | `backend/smart_agri/core/services/mass_casualty_service.py` | `backend/smart_agri/core/tests/test_sardood_scenarios.py` | `python backend/manage.py verify_release_gate_v21` | `python backend/manage.py release_readiness_snapshot` |

## Step Summary

| Group | Step | Status | Exit |
|---|---|---|---:|
| `static` | `Bootstrap/runtime contract` | `PASS` | `0` |
| `static` | `PostgreSQL foundation contract` | `PASS` | `0` |
| `static` | `Bare exception scan` | `PASS` | `0` |
| `static` | `Docx traceability coverage` | `PASS` | `0` |
| `static` | `Release hygiene static contract` | `PASS` | `0` |
| `static` | `Decimal mutation guard` | `PASS` | `0` |
| `static` | `Idempotency action contract` | `PASS` | `0` |
| `static` | `Farm scope guard contract` | `PASS` | `0` |
| `static` | `Service-layer write contract` | `PASS` | `0` |
| `static` | `Compliance docs contract` | `PASS` | `0` |
| `static` | `XLSX integrity gate` | `PASS` | `0` |
| `static` | `Float guard strict scan` | `PASS` | `0` |
| `backend_tests` | `Backend smart-card and mode tests` | `PASS` | `0` |
| `backend_tests` | `Backend approval and reopen tests` | `PASS` | `0` |
| `backend_tests` | `Backend attachment and runtime tests` | `PASS` | `0` |
| `backend_tests` | `Backend supplier settlement and mode policy tests` | `PASS` | `0` |
| `backend_tests` | `Backend contract, assets, fuel, and petty-cash tests` | `PASS` | `0` |
| `frontend` | `Frontend lint` | `PASS` | `0` |
| `frontend` | `Frontend focused Vitest suites` | `PASS` | `0` |
| `frontend` | `Frontend build` | `PASS` | `0` |
| `runtime` | `Django system checks` | `PASS` | `0` |
| `runtime` | `Seed runtime governance evidence` | `PASS` | `0` |
| `runtime` | `Django migrations status` | `PASS` | `0` |
| `runtime` | `Django migration plan` | `PASS` | `0` |
| `runtime` | `Runtime probe V21` | `PASS` | `0` |
| `runtime` | `Release readiness snapshot` | `PASS` | `0` |
| `runtime` | `Attachment scan` | `PASS` | `0` |
| `runtime` | `Due remote reviews` | `PASS` | `0` |
| `runtime` | `Persistent outbox dispatch` | `PASS` | `0` |
| `runtime` | `Persistent outbox retry dead letters` | `PASS` | `0` |
| `runtime` | `Persistent outbox purge dry-run` | `PASS` | `0` |
| `axis_static` | `Schema zombie detection` | `PASS` | `0` |
| `axis_static` | `Schema ghost trigger detection` | `PASS` | `0` |
| `axis_static` | `Backup freshness contract` | `PASS` | `0` |
| `axis_static` | `Fiscal period gate contract` | `PASS` | `0` |
| `axis_static` | `Harvest zakat trigger contract` | `PASS` | `0` |
| `axis_static` | `Solar depreciation contract` | `PASS` | `0` |
| `axis_static` | `Accounts service-layer write contract` | `PASS` | `0` |
| `axis_static` | `Auth service-layer write contract` | `PASS` | `0` |
| `axis_backend` | `Axis idempotency backend tests` | `PASS` | `0` |
| `axis_backend` | `Axis fiscal and fund backend tests` | `PASS` | `0` |
| `axis_backend` | `Axis tenant, audit, and variance backend tests` | `PASS` | `0` |
| `axis_backend` | `Axis farm tiering and workbench backend tests` | `PASS` | `0` |
| `axis_backend` | `Axis biological and harvest backend tests` | `PASS` | `0` |
| `axis_backend` | `Axis settlement, contract, and mass-casualty backend tests` | `PASS` | `0` |
| `axis_backend` | `Axis single-crop costing backend tests` | `PASS` | `0` |
| `axis_runtime` | `Axis governance maintenance dry run` | `PASS` | `0` |
| `axis_backend` | `Axis integration and account governance backend tests` | `PASS` | `0` |
| `axis_runtime` | `Axis E2E auth preparation` | `PASS` | `0` |
| `axis_frontend` | `Axis Playwright daily smart-card proof` | `PASS` | `0` |
| `axis_frontend` | `Axis Playwright supplier settlement proof` | `PASS` | `0` |
| `axis_frontend` | `Axis Playwright contract operations proof` | `PASS` | `0` |
| `axis_frontend` | `Axis Playwright fixed-assets proof` | `PASS` | `0` |
| `axis_frontend` | `Axis Playwright fuel and dual-mode proof` | `PASS` | `0` |

## Copied Artifacts

- `C:\tools\workspace\AgriAsset_v44\backend\release_readiness_snapshot.json`
- `C:\tools\workspace\AgriAsset_v44\backend\release_readiness_snapshot.md`
- `C:\tools\workspace\AgriAsset_v44\backend\scripts\release_gate_float_check.txt`
