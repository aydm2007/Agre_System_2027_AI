# Verification Commands v2 (updated for V3 candidate)

This is the readable release-gate reference when legacy doctrine files are locked or outdated.

Canonical Windows-safe wrappers:

```bash
python backend/manage.py verify_static_v21
python backend/manage.py run_closure_evidence_v21
python backend/manage.py verify_release_gate_v21
python backend/manage.py verify_axis_complete_v21
```

## Static / bootstrap gate

```bash
python scripts/verification/check_bootstrap_contract.py
python scripts/verification/check_docx_traceability.py
python scripts/verification/check_no_bare_exceptions.py
python scripts/verification/check_service_layer_writes.py
python scripts/verification/check_accounts_service_layer_writes.py
python scripts/verification/check_auth_service_layer_writes.py
python scripts/check_no_float_mutations.py
python scripts/check_idempotency_actions.py
python scripts/check_farm_scope_guards.py
python scripts/verification/check_compliance_docs.py
python scripts/verification/check_backup_freshness.py
python scripts/verification/check_restore_drill_evidence.py
python scripts/verification/detect_zombies.py
python scripts/verification/detect_ghost_triggers.py
```

## Runtime release gate

```bash
python backend/manage.py showmigrations --plan
python backend/manage.py migrate --plan
python backend/manage.py check
python backend/manage.py runtime_probe_v21
python backend/manage.py release_readiness_snapshot
python backend/manage.py scan_pending_attachments
python backend/manage.py report_due_remote_reviews
python backend/manage.py dispatch_outbox --batch-size 10 --metadata-flag seed_runtime_governance
python backend/manage.py retry_dead_letters --limit 10 --metadata-flag seed_runtime_governance
python backend/manage.py purge_dispatched_outbox --dry-run --metadata-flag seed_runtime_governance
```

## Axis-complete closure

```bash
python backend/manage.py verify_axis_complete_v21
```

This orchestrator is evidence-only. It preserves the existing canonical command roots and extends the closure run to:
- axis-linked static checks
- axis-targeted backend suites
- governance dry-run and account governance proofs
- deterministic Playwright proofs for daily smart card, supplier settlement, contract operations, fixed assets, and fuel reconciliation
- a final 18-axis summary with `code + test + gate + runtime` anchors

Windows shells should preload DB credentials before running the runtime commands:

```powershell
& .\scripts\windows\Resolve-BackendDbEnv.ps1
```

CMD shells should preload DB credentials with:

```bat
call scripts\windows\load_backend_db_env.cmd
```

Canonical Playwright verification on Windows now assumes the backend web server is started through
`frontend/playwright.config.js`, which:
- preloads PostgreSQL credentials via `scripts/windows/Resolve-BackendDbEnv.ps1`
- runs `python backend/manage.py migrate --noinput`
- only then starts Django `runserver`

This is required to keep browser proofs deterministic and to avoid false failures caused by stale
developer-local schemas.

## Workflow-Specific Gates

- Daily Execution Smart Card Stack
```bash
python backend/manage.py test smart_agri.core.tests.test_service_cards smart_agri.core.tests.test_daily_log_tree_api smart_agri.core.tests.test_tree_inventory_service smart_agri.core.tests.test_tree_inventory_sync smart_agri.core.tests.test_tree_variance smart_agri.core.tests.test_tree_census_service --keepdb --noinput
npm --prefix frontend run test -- src/components/daily-log/__tests__/DailyLogSmartCard.test.jsx src/pages/__tests__/ServiceCards.test.jsx --run
set PLAYWRIGHT_ARTIFACT_ROOT=%TEMP%\\agriasset-pw-smart-card
npx --prefix frontend playwright test frontend/tests/e2e/daily-log-smart-card.spec.js --project=chromium --config=frontend/playwright.config.js --workers=1 --reporter=line
```

- Supplemental SIMPLE expanded readiness pack
```bash
python backend/manage.py test smart_agri.core.tests.test_tree_inventory smart_agri.core.tests.test_seed_tree_inventory_endpoint smart_agri.core.tests.test_simple_mode_crop_variance_audit smart_agri.core.tests.test_al_jaruba_simple_cycle --keepdb --noinput
npm --prefix frontend run test -- src/hooks/__tests__/usePerennialLogic.test.js src/components/daily-log/__tests__/DailyLogDetails.test.jsx src/components/daily-log/__tests__/DailyLogSmartCard.test.jsx --run
npm --prefix frontend run lint
set PLAYWRIGHT_ARTIFACT_ROOT=%TEMP%\\agriasset-pw-simple-expanded
npx --prefix frontend playwright test frontend/tests/e2e/simple_mode_isolation.spec.js frontend/tests/e2e/simple-mode-governed-cycles-ar.spec.js frontend/tests/e2e/sardud_perennial_forensic_cycle.spec.js frontend/tests/e2e/daily-log-seasonal-perennial.spec.js --config=frontend/playwright.config.js --project=chromium --workers=1 --reporter=line
```
This bundle is supplemental readiness evidence for SIMPLE closure hardening. It does not replace canonical release-gate authority or the score authority of `verify_axis_complete_v21`.

- Import / Export XLSX platform first wave
```bash
python backend/manage.py test smart_agri.core.tests.test_import_export_platform --keepdb --noinput
npm --prefix frontend run test -- src/components/inventory/__tests__/InventoryImportExportCenter.test.jsx src/pages/Reports/components/__tests__/DetailedTables.test.jsx --run
npm --prefix frontend run lint
```
This bundle validates the first-wave `XLSX/JSON` import-export platform for reports and inventory. It is supporting evidence and does not replace canonical release-gate authority.

- Import / Export XLSX platform wave 2 / wave 3 registry
```bash
python backend/manage.py test smart_agri.core.tests.test_import_export_platform --keepdb --noinput
npm --prefix frontend run test -- src/components/inventory/__tests__/InventoryImportExportCenter.test.jsx src/pages/Reports/components/__tests__/DetailedTables.test.jsx --run
npm --prefix frontend run lint
```
This bundle validates the unified export registry, `Reports Hub` catalog, inventory history panels, and mode-aware module-local export metadata for wave 2 / wave 3 expansion. It is supplemental evidence and does not replace canonical release-gate authority.

- Planning import platform wave
```bash
python backend/manage.py test smart_agri.core.tests.test_import_export_platform smart_agri.core.tests.test_planning_import_platform --keepdb --noinput
npm --prefix frontend run test -- src/components/planning/__tests__/PlanningImportCenter.test.jsx --run
npm --prefix frontend run lint
```
This bundle validates that planning imports (`planning_master_schedule`, `planning_crop_plan_structure`, and strict-only `planning_crop_plan_budget`) run through the same backend-governed preview/apply platform with no authoritative frontend workbook parsing.

- Petty Cash
```bash
npm --prefix frontend run test -- src/pages/Finance/__tests__/PettyCashDashboard.test.jsx --run
set PLAYWRIGHT_ARTIFACT_ROOT=%TEMP%\\agriasset-pw-petty
npx --prefix frontend playwright test frontend/tests/e2e/petty-cash.spec.js --config=frontend/playwright.config.js --project=chromium --workers=1 --reporter=line
```

- Receipts and Deposit
```bash
npm --prefix frontend run test -- src/pages/Finance/__tests__/ReceiptsDepositDashboard.test.jsx --run
```

- SIMPLE finance shadow-ledger read surface
```bash
python backend/manage.py test smart_agri.core.tests.test_shadow_ledger_readonly --keepdb --noinput
npm --prefix frontend run test -- src/pages/Finance/__tests__/LedgerList.test.jsx src/pages/Finance/__tests__/FinancePage.test.jsx --run
curl -I "http://<host>/api/v1/shadow-ledger/?farm=<simple_farm>"
curl -I "http://<host>/api/v1/shadow-ledger/summary/?farm=<simple_farm>"
```
This bundle validates the read-only SIMPLE finance surface, the summary-first ledger UI, and the deployment smoke contract for `shadow-ledger`. A `404` on the deployed host is a frontend/backend deployment mismatch and must not be misread as a business-logic permission failure.

- Supplier Settlement
```bash
python backend/manage.py test smart_agri.finance.tests.test_supplier_settlement_api --keepdb --noinput
npm --prefix frontend run test -- src/pages/Finance/__tests__/SupplierSettlementDashboard.test.jsx --run
set PLAYWRIGHT_ARTIFACT_ROOT=%TEMP%\\agriasset-pw-supplier
npx --prefix frontend playwright test frontend/tests/e2e/supplier-settlement.spec.js --config=frontend/playwright.config.js --project=chromium --workers=1 --reporter=line
```

- Contract Operations
```bash
python backend/manage.py test smart_agri.core.tests.test_contract_operations_dashboard_api smart_agri.core.tests.test_sharecropping_posting_service --keepdb --noinput
npm --prefix frontend run test -- src/pages/__tests__/ContractOperationsDashboard.test.jsx --run
set PLAYWRIGHT_ARTIFACT_ROOT=%TEMP%\\agriasset-pw-contract
npx --prefix frontend playwright test frontend/tests/e2e/contract-operations.spec.js --config=frontend/playwright.config.js --project=chromium --workers=1 --reporter=line
```

- Fixed Assets
```bash
python backend/manage.py test smart_agri.core.tests.test_fixed_assets_dashboard_api --keepdb --noinput
npm --prefix frontend run test -- src/pages/__tests__/FixedAssetsDashboard.test.jsx --run
set PLAYWRIGHT_ARTIFACT_ROOT=%TEMP%\\agriasset-pw-fixed-assets
npx --prefix frontend playwright test frontend/tests/e2e/fixed-assets.spec.js --config=frontend/playwright.config.js --project=chromium --workers=1 --reporter=line
```

- Fuel Reconciliation
```bash
python backend/manage.py test smart_agri.core.tests.test_fuel_reconciliation_dashboard_api --keepdb --noinput
npm --prefix frontend run test -- src/pages/__tests__/FuelReconciliationDashboard.test.jsx --run
set PLAYWRIGHT_ARTIFACT_ROOT=%TEMP%\\agriasset-pw-fuel
npx --prefix frontend playwright test frontend/tests/e2e/fuel-reconciliation.spec.js frontend/tests/e2e/dual-mode-switch.spec.js --config=frontend/playwright.config.js --project=chromium --workers=1 --reporter=line
```

- Supplemental paired Arabic UAT pack (`simple-farm` / `strict-farm`)
```bash
python backend/manage.py seed_rabouia_uat --clean
python backend/manage.py seed_sarima_uat --clean
python backend/manage.py test smart_agri.core.tests.test_rabouia_sarima_uat --keepdb --noinput
npm --prefix frontend run lint
set PLAYWRIGHT_ARTIFACT_ROOT=%TEMP%\\agriasset-pw-rabouia-sarima
npx --prefix frontend playwright test frontend/tests/e2e/rabouia-simple-cycle.spec.js frontend/tests/e2e/sarima-strict-cycle.spec.js frontend/tests/e2e/rabouia-sarima-reports.spec.js --config=frontend/playwright.config.js --project=chromium --workers=1 --reporter=line
python backend/manage.py run_rabouia_sarima_uat --artifact-root docs/evidence/uat/rabouia-sarima/latest --clean-seed
```
This bundle is supplemental UAT evidence. It validates Arabic seed data and dual-mode scenario coverage for:
- `simple-farm profile`: `SMALL + SIMPLE + custody/offline + smart_card_stack + posture-only finance`
- `strict-farm profile`: `LARGE + STRICT + procurement + petty cash + receipts + supplier settlement + fixed assets + fuel + harvest + contract operations + governance workbench + attachments`

The management command names and artifact slugs remain the current operational identifiers for this paired UAT pack. The narrative labels above are intentionally generic and must not be read as farm-specific doctrine.

It does not replace the canonical score authority of `verify_axis_complete_v21`.

- Attachments / Forensics
```bash
python backend/manage.py scan_pending_attachments
python backend/manage.py run_governance_maintenance_cycle --dry-run
python backend/manage.py test smart_agri.core.tests.test_attachment_policy_service smart_agri.core.tests.test_v18_attachment_hardening smart_agri.core.tests.test_v19_attachment_filename_guard smart_agri.core.tests.test_v20_attachment_lifecycle smart_agri.core.tests.test_v21_attachment_runtime_contract --keepdb --noinput
```

- Approvals / Workbench / Sector Governance
```bash
python backend/manage.py report_due_remote_reviews
python backend/manage.py test smart_agri.finance.tests.test_approval_workflow_api smart_agri.finance.tests.test_approval_state_transitions smart_agri.finance.tests.test_approval_override_and_reopen --keepdb --noinput
```

- Outbox / Integration Hub
```bash
python backend/manage.py dispatch_outbox --batch-size 10 --metadata-flag seed_runtime_governance
python backend/manage.py retry_dead_letters --limit 10 --metadata-flag seed_runtime_governance
python backend/manage.py purge_dispatched_outbox --dry-run --metadata-flag seed_runtime_governance
python backend/manage.py test smart_agri.core.tests.test_integration_hub_contracts --keepdb --noinput
```

- Accounts Governance, Membership, and Auth
```bash
python scripts/verification/check_accounts_service_layer_writes.py
python scripts/verification/check_auth_service_layer_writes.py
python backend/manage.py test smart_agri.accounts.tests.test_memberships_api smart_agri.accounts.tests.test_role_delegation --keepdb --noinput
```

## Reference Integrity

- If the legacy verification doc is unreadable or write-locked, use this file as the readable canonical reference until the legacy file can be repaired.
- Blocked script output files must be documented in readiness evidence; otherwise the workflow remains `BLOCKED`.
- The Windows release gate currently invokes `npm --prefix frontend run test:ci` for frontend CI stability. Mark the frontend test axis complete only when that command passes end-to-end in the active readiness run.
- Fixed-assets and fuel-reconciliation workflow closure now expects both seeded runtime evidence (`runtime_probe_v21`, `release_readiness_snapshot`) and governed backend action tests, not dashboard rendering alone.
- Runtime release verification now uses `INTEGRATION_HUB_PUBLISHER=readiness_composite` for seeded self-contained outbox success, retryable, and dead-letter evidence without an external webhook listener.
- Canonical Playwright closure runs may set `PLAYWRIGHT_ARTIFACT_ROOT` to an isolated writable temp directory; this avoids false `BLOCKED` states from write-locked repository artifact folders.
- Attachment and governance closure now expects scenario-complete evidence for clean, quarantine, archive, legal-hold, restore, and purge-eligible paths, not policy prose alone.
- Role/workbench closure now expects explicit distinction between farm chief accountant, farm finance manager, sector chief accountant, and sector finance director in both reference and tests.
- `100/100` is only claimable when `python backend/manage.py verify_axis_complete_v21` finishes with both `overall_status=PASS` and `axis_overall_status=PASS`.
