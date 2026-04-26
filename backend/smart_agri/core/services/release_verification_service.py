from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_BLOCKED_PATTERNS = (
    "fe_sendauth",
    "no password supplied",
    "password authentication failed",
    "connection refused",
    "could not connect to server",
    "econnrefused",
    "module not found",
    "modulenotfounderror",
    "importerror: couldn't import django",
    "wsl",
    "no installed distributions",
    "make is not recognized",
    "timeout expired",
    "executable doesn't exist",
)


@dataclass(frozen=True)
class VerificationStep:
    key: str
    label: str
    group: str
    command: tuple[str, ...]
    cwd: str = "."
    timeout_seconds: int | None = None
    blocked_patterns: tuple[str, ...] = DEFAULT_BLOCKED_PATTERNS
    env_overrides: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class AxisDefinition:
    number: int
    key: str
    title: str
    code_anchor: str
    test_anchor: str
    gate_anchor: str
    runtime_anchor: str
    step_keys: tuple[str, ...]


def repo_root_from_backend_dir(base_dir: Path) -> Path:
    return Path(base_dir).resolve().parent


def command_string(command: tuple[str, ...]) -> str:
    return shlex.join(command)


def suite_overall_status(steps: list[dict]) -> str:
    statuses = {item["status"] for item in steps}
    if "FAIL" in statuses:
        return "FAIL"
    if "BLOCKED" in statuses:
        return "BLOCKED"
    return "PASS"


def build_static_steps(repo_root: Path) -> list[VerificationStep]:
    python = sys.executable
    return [
        VerificationStep("bootstrap_contract", "Bootstrap/runtime contract", "static", (python, "scripts/verification/check_bootstrap_contract.py")),
        VerificationStep("postgres_foundation", "PostgreSQL foundation contract", "static", (python, "scripts/verification/verify_postgres_foundation_contract.py")),
        VerificationStep("bare_exceptions", "Bare exception scan", "static", (python, "scripts/verification/check_no_bare_exceptions.py")),
        VerificationStep("docx_traceability", "Docx traceability coverage", "static", (python, "scripts/verification/check_docx_traceability.py")),
        VerificationStep("release_hygiene", "Release hygiene static contract", "static", (python, "scripts/verification/verify_release_hygiene.py")),
        VerificationStep("decimal_mutations", "Decimal mutation guard", "static", (python, "scripts/check_no_float_mutations.py")),
        VerificationStep("idempotency_actions", "Idempotency action contract", "static", (python, "scripts/check_idempotency_actions.py")),
        VerificationStep("farm_scope_guards", "Farm scope guard contract", "static", (python, "scripts/check_farm_scope_guards.py")),
        VerificationStep("service_layer_writes", "Service-layer write contract", "static", (python, "scripts/verification/check_service_layer_writes.py")),
        VerificationStep("compliance_docs", "Compliance docs contract", "static", (python, "scripts/verification/check_compliance_docs.py")),
        VerificationStep("xlsx_gate_check", "XLSX integrity gate", "static", (python, "scripts/verification/check_xlsx_gate.py")),
    ]


def build_closure_evidence_steps(repo_root: Path, *, skip_frontend: bool = False) -> list[VerificationStep]:
    python = sys.executable
    npm = _npm_executable()
    steps = [
        VerificationStep("django_check", "Django system checks", "runtime", (python, "backend/manage.py", "check", "--deploy")),
        VerificationStep("seed_runtime_evidence", "Seed runtime governance evidence", "runtime", (python, "backend/manage.py", "seed_runtime_governance_evidence")),
        VerificationStep("showmigrations_plan", "Django migrations status", "runtime", (python, "backend/manage.py", "showmigrations", "--plan"), timeout_seconds=60),
        VerificationStep("migrate_plan", "Django migration plan", "runtime", (python, "backend/manage.py", "migrate", "--plan"), timeout_seconds=60),
        VerificationStep("runtime_probe_v21", "Runtime probe V21", "runtime", (python, "backend/manage.py", "runtime_probe_v21"), timeout_seconds=60),
        VerificationStep("release_readiness_snapshot", "Release readiness snapshot", "runtime", (python, "backend/manage.py", "release_readiness_snapshot"), timeout_seconds=60),
        VerificationStep("scan_pending_attachments", "Attachment scan", "runtime", (python, "backend/manage.py", "scan_pending_attachments"), timeout_seconds=60),
        VerificationStep("report_due_remote_reviews", "Due remote reviews", "runtime", (python, "backend/manage.py", "report_due_remote_reviews"), timeout_seconds=60),
        VerificationStep(
            "dispatch_outbox",
            "Persistent outbox dispatch",
            "runtime",
            (python, "backend/manage.py", "dispatch_outbox", "--batch-size", "10", "--metadata-flag", "seed_runtime_governance"),
            timeout_seconds=60,
        ),
        VerificationStep(
            "retry_dead_letters",
            "Persistent outbox retry dead letters",
            "runtime",
            (python, "backend/manage.py", "retry_dead_letters", "--limit", "10", "--metadata-flag", "seed_runtime_governance"),
            timeout_seconds=60,
        ),
        VerificationStep(
            "purge_dispatched_outbox",
            "Persistent outbox purge dry-run",
            "runtime",
            (python, "backend/manage.py", "purge_dispatched_outbox", "--dry-run", "--metadata-flag", "seed_runtime_governance"),
            timeout_seconds=60,
        ),
    ]
    if not skip_frontend:
        steps.extend(
            [
                VerificationStep("frontend_lint", "Frontend lint", "frontend", (npm, "--prefix", "frontend", "run", "lint"), timeout_seconds=120),
                VerificationStep("frontend_test_ci", "Frontend test CI", "frontend", (npm, "--prefix", "frontend", "run", "test:ci"), timeout_seconds=600),
                VerificationStep("frontend_build", "Frontend build", "frontend", (npm, "--prefix", "frontend", "run", "build"), timeout_seconds=300),
            ]
        )
    return steps


def build_release_gate_steps(repo_root: Path, *, skip_frontend: bool = False) -> list[VerificationStep]:
    python = sys.executable
    npm = _npm_executable()
    steps = build_static_steps(repo_root)
    steps.extend(
        [
            VerificationStep("float_guard_strict", "Float guard strict scan", "static", (python, "backend/scripts/float_guard.py", "--strict")),
            VerificationStep("backend_smart_card_mode_tests", "Backend smart-card and mode tests", "backend_tests", (python, "backend/manage.py", "test", "smart_agri.core.tests.test_service_cards", "smart_agri.core.tests.test_simple_strict_separation", "--keepdb", "--noinput"), timeout_seconds=600),
            VerificationStep("backend_approval_tests", "Backend approval and reopen tests", "backend_tests", (python, "backend/manage.py", "test", "smart_agri.finance.tests.test_approval_workflow_api", "smart_agri.finance.tests.test_approval_override_and_reopen", "--keepdb", "--noinput"), timeout_seconds=600),
            VerificationStep("backend_attachment_tests", "Backend attachment and runtime tests", "backend_tests", (python, "backend/manage.py", "test", "smart_agri.core.tests.test_attachment_policy_service", "smart_agri.core.tests.test_attachment_lifecycle_v21", "smart_agri.core.tests.test_v18_attachment_hardening", "smart_agri.core.tests.test_v19_remote_review_snapshot", "--keepdb", "--noinput"), timeout_seconds=600),
            VerificationStep("backend_supplier_mode_tests", "Backend supplier settlement and mode policy tests", "backend_tests", (python, "backend/manage.py", "test", "smart_agri.finance.tests.test_supplier_settlement_api", "smart_agri.finance.tests.test_v15_profiled_posting_authority", "smart_agri.core.tests.test_mode_policy_api", "--keepdb", "--noinput"), timeout_seconds=600),
            VerificationStep("backend_contract_asset_fuel_cash_tests", "Backend contract, assets, fuel, and petty-cash tests", "backend_tests", (python, "backend/manage.py", "test", "smart_agri.core.tests.test_contract_operations_dashboard_api", "smart_agri.core.tests.test_sharecropping_posting_service", "smart_agri.core.tests.test_fixed_assets_dashboard_api", "smart_agri.core.tests.test_fuel_reconciliation_dashboard_api", "smart_agri.finance.tests.test_petty_cash_service", "smart_agri.finance.tests.test_petty_cash_settlement", "--keepdb", "--noinput"), timeout_seconds=600),
        ]
    )
    if not skip_frontend:
        steps.extend(
            [
                VerificationStep("frontend_lint", "Frontend lint", "frontend", (npm, "--prefix", "frontend", "run", "lint"), timeout_seconds=120),
                VerificationStep("frontend_focused_vitest", "Frontend focused Vitest suites", "frontend", (npm, "--prefix", "frontend", "run", "test", "--", "src/components/daily-log/__tests__/DailyLogSmartCard.test.jsx", "src/pages/__tests__/ServiceCards.test.jsx", "src/pages/Finance/__tests__/SupplierSettlementDashboard.test.jsx", "src/pages/__tests__/ContractOperationsDashboard.test.jsx", "src/pages/__tests__/FixedAssetsDashboard.test.jsx", "src/pages/__tests__/FuelReconciliationDashboard.test.jsx", "src/pages/Finance/__tests__/PettyCashDashboard.test.jsx", "src/pages/Finance/__tests__/ReceiptsDepositDashboard.test.jsx", "--run"), timeout_seconds=600),
                VerificationStep("frontend_build", "Frontend build", "frontend", (npm, "--prefix", "frontend", "run", "build"), timeout_seconds=300),
            ]
        )
    steps.extend(build_closure_evidence_steps(repo_root, skip_frontend=True))
    return steps


def build_axis_complete_steps(repo_root: Path, *, skip_frontend: bool = False) -> list[VerificationStep]:
    python = sys.executable
    npx = _npx_executable()
    playwright_env = (("PLAYWRIGHT_ARTIFACT_ROOT", "{suite_tmp}"),)
    steps = build_release_gate_steps(repo_root, skip_frontend=skip_frontend)
    steps.extend(
        [
            VerificationStep("schema_detect_zombies", "Schema zombie detection", "axis_static", (python, "scripts/verification/detect_zombies.py"), timeout_seconds=60),
            VerificationStep("schema_detect_ghost_triggers", "Schema ghost trigger detection", "axis_static", (python, "scripts/verification/detect_ghost_triggers.py"), timeout_seconds=60),
            VerificationStep("backup_freshness", "Backup freshness contract", "axis_static", (python, "scripts/verification/check_backup_freshness.py"), timeout_seconds=60),
            # VerificationStep("restore_drill_evidence", "Restore drill evidence contract", "axis_static", (python, "scripts/verification/check_restore_drill_evidence.py"), timeout_seconds=60),
            VerificationStep("fiscal_period_gates", "Fiscal period gate contract", "axis_static", (python, "scripts/check_fiscal_period_gates.py"), timeout_seconds=60),
            VerificationStep("zakat_harvest_triggers", "Harvest zakat trigger contract", "axis_static", (python, "backend/scripts/check_zakat_harvest_triggers.py"), timeout_seconds=60),
            VerificationStep("solar_depreciation_logic", "Solar depreciation contract", "axis_static", (python, "backend/scripts/check_solar_depreciation_logic.py"), timeout_seconds=60),
            VerificationStep("accounts_service_layer_writes", "Accounts service-layer write contract", "axis_static", (python, "scripts/verification/check_accounts_service_layer_writes.py"), timeout_seconds=60),
            VerificationStep("auth_service_layer_writes", "Auth service-layer write contract", "axis_static", (python, "scripts/verification/check_auth_service_layer_writes.py"), timeout_seconds=60),
            VerificationStep("axis_idempotency_tests", "Axis idempotency backend tests", "axis_backend", (python, "backend/manage.py", "test", "smart_agri.core.tests.test_idempotency_middleware", "smart_agri.finance.tests.test_fiscal_year_rollover_idempotency", "smart_agri.core.tests.test_zakat_policy_v2", "--keepdb", "--noinput"), timeout_seconds=900),
            VerificationStep("axis_fiscal_fund_tests", "Axis fiscal and fund backend tests", "axis_backend", (python, "backend/manage.py", "test", "smart_agri.finance.tests.test_fiscal_lifecycle", "smart_agri.finance.tests.test_fiscal_close_governance", "smart_agri.core.tests.test_fiscal_close_e2e", "smart_agri.core.tests.test_financial_governance", "smart_agri.finance.tests.test_financial_integrity_governance", "--keepdb", "--noinput"), timeout_seconds=900),
            VerificationStep("axis_tenant_audit_variance_tests", "Axis tenant, audit, and variance backend tests", "axis_backend", (python, "backend/manage.py", "test", "smart_agri.finance.tests.test_tenant_isolation", "smart_agri.core.tests.test_rls_authorization", "smart_agri.core.tests.test_phase7_audit_append_only", "smart_agri.core.tests.test_route_breach_middleware", "smart_agri.core.tests.test_schedule_variance", "smart_agri.core.tests.test_phase5_variance_workflow", "--keepdb", "--noinput"), timeout_seconds=900),
            VerificationStep("axis_tiering_workbench_tests", "Axis farm tiering and workbench backend tests", "axis_backend", (python, "backend/manage.py", "test", "smart_agri.core.tests.test_farm_size_governance", "smart_agri.core.tests.test_v21_governance_comprehensive", "smart_agri.finance.tests.test_v18_role_workbench", "smart_agri.finance.tests.test_v21_role_workbench", "smart_agri.accounts.tests.test_role_delegation", "--keepdb", "--noinput"), timeout_seconds=900),
            VerificationStep("axis_biological_harvest_tests", "Axis biological and harvest backend tests", "axis_backend", (python, "backend/manage.py", "test", "smart_agri.core.tests.test_biological_asset_impairment", "smart_agri.core.tests.test_tree_inventory", "smart_agri.core.tests.test_phase6_zakat_solar", "smart_agri.core.tests.test_harvest_products", "smart_agri.core.tests.test_activity_requirements", "smart_agri.sales.tests.test_sale_service", "--keepdb", "--noinput"), timeout_seconds=900),
            VerificationStep("axis_settlement_contract_mass_tests", "Axis settlement, contract, and mass-casualty backend tests", "axis_backend", (python, "backend/manage.py", "test", "smart_agri.core.tests.test_seasonal_settlement", "smart_agri.core.tests.test_operational_contracts", "smart_agri.core.tests.test_shadow_accounting_strict", "smart_agri.core.tests.test_sardood_scenarios", "--keepdb", "--noinput"), timeout_seconds=900),
            VerificationStep("axis_single_crop_tests", "Axis single-crop costing backend tests", "axis_backend", (python, "backend/manage.py", "test", "smart_agri.core.tests.test_activity_cost_snapshot_integrity", "smart_agri.core.tests.test_service_cards", "smart_agri.core.tests.test_v21_e2e_cycle", "--keepdb", "--noinput"), timeout_seconds=900),
            VerificationStep("axis_governance_maintenance_dry_run", "Axis governance maintenance dry run", "axis_runtime", (python, "backend/manage.py", "run_governance_maintenance_cycle", "--dry-run"), timeout_seconds=120),
            VerificationStep("axis_integration_accounts_tests", "Axis integration and account governance backend tests", "axis_backend", (python, "backend/manage.py", "test", "smart_agri.core.tests.test_integration_hub_contracts", "smart_agri.accounts.tests.test_memberships_api", "smart_agri.accounts.tests.test_role_delegation", "--keepdb", "--noinput"), timeout_seconds=900),
            VerificationStep("axis_prepare_e2e_auth", "Axis E2E auth preparation", "axis_runtime", (python, "backend/manage.py", "prepare_e2e_auth_v21"), timeout_seconds=120),
        ]
    )
    if not skip_frontend:
        steps.extend(
            [
                VerificationStep(
                    "axis_playwright_daily_log",
                    "Axis Playwright daily smart-card proof",
                    "axis_frontend",
                    (npx, "--prefix", "frontend", "playwright", "test", "frontend/tests/e2e/daily-log-smart-card.spec.js", "--project=chromium", "--config=frontend/playwright.config.js", "--workers=1", "--reporter=line"),
                    timeout_seconds=900,
                    env_overrides=playwright_env,
                ),
                VerificationStep(
                    "axis_playwright_supplier",
                    "Axis Playwright supplier settlement proof",
                    "axis_frontend",
                    (npx, "--prefix", "frontend", "playwright", "test", "frontend/tests/e2e/supplier-settlement.spec.js", "--project=chromium", "--config=frontend/playwright.config.js", "--workers=1", "--reporter=line"),
                    timeout_seconds=900,
                    env_overrides=playwright_env,
                ),
                VerificationStep(
                    "axis_playwright_contract",
                    "Axis Playwright contract operations proof",
                    "axis_frontend",
                    (npx, "--prefix", "frontend", "playwright", "test", "frontend/tests/e2e/contract-operations.spec.js", "--project=chromium", "--config=frontend/playwright.config.js", "--workers=1", "--reporter=line"),
                    timeout_seconds=900,
                    env_overrides=playwright_env,
                ),
                VerificationStep(
                    "axis_playwright_fixed_assets",
                    "Axis Playwright fixed-assets proof",
                    "axis_frontend",
                    (npx, "--prefix", "frontend", "playwright", "test", "frontend/tests/e2e/fixed-assets.spec.js", "--project=chromium", "--config=frontend/playwright.config.js", "--workers=1", "--reporter=line"),
                    timeout_seconds=900,
                    env_overrides=playwright_env,
                ),
                VerificationStep(
                    "axis_playwright_fuel",
                    "Axis Playwright fuel and dual-mode proof",
                    "axis_frontend",
                    (npx, "--prefix", "frontend", "playwright", "test", "frontend/tests/e2e/fuel-reconciliation.spec.js", "frontend/tests/e2e/dual-mode-switch.spec.js", "--project=chromium", "--config=frontend/playwright.config.js", "--workers=1", "--reporter=line"),
                    timeout_seconds=900,
                    env_overrides=playwright_env,
                ),
            ]
        )
    return steps


def build_axis_definitions() -> list[AxisDefinition]:
    return [
        AxisDefinition(1, "schema_parity", "Schema Parity", "backend/smart_agri/core/migrations/, backend/smart_agri/finance/migrations/", "backend/smart_agri/core/tests/test_schema_parity_runtime.py", "python scripts/verification/detect_zombies.py ; python scripts/verification/detect_ghost_triggers.py", "python backend/manage.py showmigrations --plan ; python backend/manage.py migrate --plan", ("postgres_foundation", "showmigrations_plan", "migrate_plan", "schema_detect_zombies", "schema_detect_ghost_triggers")),
        AxisDefinition(2, "idempotency_v2", "Idempotency V2", "backend idempotency middleware and financial mutation services", "backend/smart_agri/core/tests/test_idempotency_middleware.py ; backend/smart_agri/finance/tests/test_fiscal_year_rollover_idempotency.py", "python scripts/check_idempotency_actions.py", "python backend/manage.py verify_release_gate_v21", ("idempotency_actions", "axis_idempotency_tests")),
        AxisDefinition(3, "fiscal_lifecycle", "Fiscal Lifecycle", "backend/smart_agri/finance/services/fiscal_*", "backend/smart_agri/finance/tests/test_fiscal_lifecycle.py ; backend/smart_agri/core/tests/test_fiscal_close_e2e.py", "python scripts/check_fiscal_period_gates.py", "python backend/manage.py release_readiness_snapshot", ("fiscal_period_gates", "axis_fiscal_fund_tests", "release_readiness_snapshot")),
        AxisDefinition(4, "fund_accounting", "Fund Accounting", "backend/smart_agri/core/services/financial_governance.py ; backend/smart_agri/finance/services/fiscal_fund_governance_service.py", "backend/smart_agri/core/tests/test_financial_governance.py ; backend/smart_agri/finance/tests/test_financial_integrity_governance.py", "python backend/manage.py verify_release_gate_v21", "python backend/manage.py release_readiness_snapshot", ("axis_fiscal_fund_tests", "release_readiness_snapshot")),
        AxisDefinition(5, "decimal_and_surra", "Decimal and Surra", "backend/smart_agri/core/services/costing.py ; finance/api_ledger_support.py", "backend/smart_agri/core/tests/test_strict_decimals.py ; backend/smart_agri/core/tests/test_labor_estimation_api.py", "python scripts/check_no_float_mutations.py ; python backend/scripts/float_guard.py --strict", "python backend/manage.py verify_static_v21", ("decimal_mutations", "float_guard_strict", "axis_single_crop_tests")),
        AxisDefinition(6, "tenant_isolation", "Tenant Isolation", "backend farm scope middleware and PostgreSQL RLS policies", "backend/smart_agri/finance/tests/test_tenant_isolation.py ; backend/smart_agri/core/tests/test_rls_authorization.py", "python scripts/check_farm_scope_guards.py", "python backend/manage.py runtime_probe_v21", ("farm_scope_guards", "axis_tenant_audit_variance_tests", "runtime_probe_v21")),
        AxisDefinition(7, "auditability", "Auditability", "backend/smart_agri/core/models/log.py::AuditLog ; append-only ledger flows", "backend/smart_agri/core/tests/test_phase7_audit_append_only.py ; backend/smart_agri/core/tests/test_route_breach_middleware.py", "python scripts/verification/check_service_layer_writes.py", "python backend/manage.py verify_release_gate_v21", ("service_layer_writes", "axis_tenant_audit_variance_tests")),
        AxisDefinition(8, "variance_and_bom", "Variance and BOM", "backend/smart_agri/core/services/schedule_variance_service.py ; DailyLog governance services", "backend/smart_agri/core/tests/test_schedule_variance.py ; backend/smart_agri/core/tests/test_phase5_variance_workflow.py", "python backend/manage.py verify_release_gate_v21", "python backend/manage.py runtime_probe_v21", ("axis_tenant_audit_variance_tests", "runtime_probe_v21", "axis_playwright_daily_log")),
        AxisDefinition(9, "sovereign_and_zakat", "Sovereign and Zakat", "backend/smart_agri/core/services/zakat_policy.py ; sovereign_zakat_service.py", "backend/smart_agri/core/tests/test_phase6_zakat_solar.py ; backend/smart_agri/core/tests/test_zakat_policy_v2.py ; backend/smart_agri/sales/tests/test_sale_service.py", "python backend/scripts/check_zakat_harvest_triggers.py ; python backend/scripts/check_solar_depreciation_logic.py", "python backend/manage.py runtime_probe_v21", ("zakat_harvest_triggers", "solar_depreciation_logic", "axis_biological_harvest_tests", "runtime_probe_v21")),
        AxisDefinition(10, "farm_tiering", "Farm Tiering", "backend farm-size governance services and accounts delegation services", "backend/smart_agri/core/tests/test_farm_size_governance.py ; backend/smart_agri/core/tests/test_v21_governance_comprehensive.py ; backend/smart_agri/accounts/tests/test_role_delegation.py", "python scripts/verification/check_compliance_docs.py", "python backend/manage.py run_governance_maintenance_cycle --dry-run", ("compliance_docs", "axis_tiering_workbench_tests", "axis_governance_maintenance_dry_run")),
        AxisDefinition(11, "biological_assets", "Biological Assets", "backend tree inventory and impairment services", "backend/smart_agri/core/tests/test_biological_asset_impairment.py ; backend/smart_agri/core/tests/test_tree_inventory.py", "python backend/manage.py verify_release_gate_v21", "python backend/manage.py release_readiness_snapshot", ("axis_biological_harvest_tests", "release_readiness_snapshot")),
        AxisDefinition(12, "harvest_compliance", "Harvest Compliance", "backend harvest services and sales integration", "backend/smart_agri/core/tests/test_harvest_products.py ; backend/smart_agri/core/tests/test_activity_requirements.py ; backend/smart_agri/core/tests/test_zakat_policy_v2.py", "python backend/scripts/check_zakat_harvest_triggers.py", "python backend/manage.py runtime_probe_v21", ("zakat_harvest_triggers", "axis_biological_harvest_tests")),
        AxisDefinition(13, "seasonal_settlement", "Seasonal Settlement", "backend/smart_agri/core/services/seasonal_settlement_service.py", "backend/smart_agri/core/tests/test_seasonal_settlement.py", "python backend/manage.py verify_release_gate_v21", "python backend/manage.py release_readiness_snapshot", ("axis_settlement_contract_mass_tests", "release_readiness_snapshot")),
        AxisDefinition(14, "schedule_variance", "Schedule Variance", "backend/smart_agri/core/services/schedule_variance_service.py", "backend/smart_agri/core/tests/test_schedule_variance.py", "python backend/manage.py verify_release_gate_v21", "npx --prefix frontend playwright test frontend/tests/e2e/daily-log-smart-card.spec.js", ("axis_tenant_audit_variance_tests", "axis_playwright_daily_log")),
        AxisDefinition(15, "sharecropping", "Sharecropping", "backend sharecropping services and contract operations service", "backend/smart_agri/core/tests/test_operational_contracts.py ; backend/smart_agri/core/tests/test_sharecropping_posting_service.py", "python backend/manage.py verify_release_gate_v21", "npx --prefix frontend playwright test frontend/tests/e2e/contract-operations.spec.js", ("axis_settlement_contract_mass_tests", "axis_playwright_contract")),
        AxisDefinition(16, "single_crop_costing", "Single-Crop Costing", "backend activity cost snapshot and smart-card contract", "backend/smart_agri/core/tests/test_activity_cost_snapshot_integrity.py ; backend/smart_agri/core/tests/test_v21_e2e_cycle.py", "python scripts/check_no_float_mutations.py", "npx --prefix frontend playwright test frontend/tests/e2e/daily-log-smart-card.spec.js", ("axis_single_crop_tests", "axis_playwright_daily_log")),
        AxisDefinition(17, "petty_cash_settlement", "Petty Cash Settlement", "backend/smart_agri/finance/services/petty_cash_service.py", "backend/smart_agri/finance/tests/test_petty_cash_service.py ; backend/smart_agri/finance/tests/test_petty_cash_settlement.py", "python backend/manage.py verify_release_gate_v21", "python backend/manage.py release_readiness_snapshot", ("backend_contract_asset_fuel_cash_tests", "release_readiness_snapshot")),
        AxisDefinition(18, "mass_exterminations", "Mass Exterminations", "backend/smart_agri/core/services/mass_casualty_service.py", "backend/smart_agri/core/tests/test_sardood_scenarios.py", "python backend/manage.py verify_release_gate_v21", "python backend/manage.py release_readiness_snapshot", ("axis_settlement_contract_mass_tests", "release_readiness_snapshot")),
    ]


def execute_suite(
    *,
    repo_root: Path,
    command_name: str,
    title: str,
    steps: list[VerificationStep],
    artifact_paths: tuple[str, ...] = (),
    axis_definitions: list[AxisDefinition] | None = None,
) -> dict:
    repo_root = Path(repo_root).resolve()
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    suite_dir = repo_root.joinpath("docs", "evidence", "closure", stamp, command_name)
    latest_dir = repo_root.joinpath("docs", "evidence", "closure", "latest", command_name)
    logs_dir = suite_dir.joinpath("logs")
    latest_logs_dir = latest_dir.joinpath("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    latest_logs_dir.mkdir(parents=True, exist_ok=True)

    env = _build_command_env(repo_root)
    results: list[dict] = []
    latest_sync_warnings: list[dict] = []
    for step in steps:
        result = _run_step(
            step=step,
            repo_root=repo_root,
            env=env,
            logs_dir=logs_dir,
            latest_logs_dir=latest_logs_dir,
            latest_sync_warnings=latest_sync_warnings,
        )
        results.append(result)

    copied_artifacts = _copy_artifacts(
        repo_root=repo_root,
        suite_dir=suite_dir,
        latest_dir=latest_dir,
        relative_paths=artifact_paths,
        latest_sync_warnings=latest_sync_warnings,
    )
    summary = {
        "command_name": command_name,
        "title": title,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "overall_status": suite_overall_status(results),
        "repo_root": str(repo_root),
        "suite_dir": str(suite_dir),
        "latest_dir": str(latest_dir),
        "counts": {
            "pass": sum(1 for item in results if item["status"] == "PASS"),
            "fail": sum(1 for item in results if item["status"] == "FAIL"),
            "blocked": sum(1 for item in results if item["status"] == "BLOCKED"),
            "total": len(results),
        },
        "steps": results,
        "artifacts": copied_artifacts,
    }
    if latest_sync_warnings:
        summary["latest_sync_warnings"] = latest_sync_warnings
    if axis_definitions:
        axis_results = build_axis_results(axis_definitions=axis_definitions, steps=results)
        summary["axes"] = axis_results
        summary["axis_counts"] = {
            "pass": sum(1 for item in axis_results if item["status"] == "PASS"),
            "fail": sum(1 for item in axis_results if item["status"] == "FAIL"),
            "blocked": sum(1 for item in axis_results if item["status"] == "BLOCKED"),
            "total": len(axis_results),
        }
        summary["axis_overall_status"] = suite_overall_status(axis_results)
    summary_write_warnings = _write_suite_summary(summary=summary, suite_dir=suite_dir, latest_dir=latest_dir)
    if summary_write_warnings:
        summary.setdefault("latest_sync_warnings", []).extend(summary_write_warnings)
        _write_primary_suite_summary(summary=summary, suite_dir=suite_dir)
    return summary


def build_axis_results(*, axis_definitions: list[AxisDefinition], steps: list[dict]) -> list[dict]:
    step_lookup = {step["key"]: step for step in steps}
    results: list[dict] = []
    for axis in axis_definitions:
        matched_steps = [step_lookup[key] for key in axis.step_keys if key in step_lookup]
        missing_steps = [key for key in axis.step_keys if key not in step_lookup]
        if missing_steps or not matched_steps:
            status = "BLOCKED"
        else:
            status = suite_overall_status(matched_steps)
        results.append(
            {
                "number": axis.number,
                "key": axis.key,
                "title": axis.title,
                "status": status,
                "code_anchor": axis.code_anchor,
                "test_anchor": axis.test_anchor,
                "gate_anchor": axis.gate_anchor,
                "runtime_anchor": axis.runtime_anchor,
                "step_keys": list(axis.step_keys),
                "missing_step_keys": missing_steps,
                "step_results": [
                    {
                        "key": step["key"],
                        "status": step["status"],
                        "label": step["label"],
                        "log_path": step["log_path"],
                    }
                    for step in matched_steps
                ],
            }
        )
    return results


def _build_command_env(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("INTEGRATION_HUB_PUBLISHER", "readiness_composite")
    env.setdefault("E2E_USER", "ibrahim")
    env.setdefault("E2E_PASS", "123456")
    env.setdefault("AGRIASSET_E2E_USER_PASSWORD", env["E2E_PASS"])
    backend_env = repo_root.joinpath("backend", ".env")
    if backend_env.exists():
        for raw_line in backend_env.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    if env.get("DB_PASSWORD") and not env.get("PGPASSWORD"):
        env["PGPASSWORD"] = env["DB_PASSWORD"]
    return env


def _run_step(
    *,
    step: VerificationStep,
    repo_root: Path,
    env: dict[str, str],
    logs_dir: Path,
    latest_logs_dir: Path,
    latest_sync_warnings: list[dict],
) -> dict:
    log_name = f"{step.key}.log"
    log_path = logs_dir.joinpath(log_name)
    latest_log_path = latest_logs_dir.joinpath(log_name)
    command_text = command_string(step.command)
    step_env, resolved_env_overrides = _resolve_step_env(step=step, env=env, suite_dir=logs_dir.parent)
    output = ""
    exit_code = 0
    status = "PASS"
    try:
        completed = subprocess.run(
            list(step.command),
            cwd=str(repo_root.joinpath(step.cwd).resolve()),
            env=step_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=step.timeout_seconds,
            check=False,
        )
        output = ((completed.stdout or "") + (completed.stderr or "")).strip()
        exit_code = completed.returncode
        status = _classify_status(exit_code=exit_code, output=output, blocked_patterns=step.blocked_patterns)
    except FileNotFoundError as exc:
        output = str(exc)
        exit_code = 127
        status = "BLOCKED"
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + (exc.stderr or "")).strip()
        exit_code = 124
        status = "BLOCKED"

    body = [
        f"== {step.label} ==",
        f"command: {command_text}",
        f"status: {status}",
        f"exit_code: {exit_code}",
    ]
    if resolved_env_overrides:
        body.append(f"env_overrides: {json.dumps(resolved_env_overrides, ensure_ascii=False, sort_keys=True)}")
    if output:
        body.extend(["", output])
    text = "\n".join(body) + "\n"
    log_path.write_text(text, encoding="utf-8")
    actual_latest_log_path = _mirror_text_to_latest(
        text=text,
        latest_path=latest_log_path,
        latest_sync_warnings=latest_sync_warnings,
        mirror_kind="step_log",
    )
    return {
        "key": step.key,
        "label": step.label,
        "group": step.group,
        "command": command_text,
        "cwd": step.cwd,
        "timeout_seconds": step.timeout_seconds,
        "env_overrides": resolved_env_overrides,
        "status": status,
        "exit_code": exit_code,
        "log_path": str(log_path),
        "latest_log_path": str(actual_latest_log_path),
    }


def _resolve_step_env(*, step: VerificationStep, env: dict[str, str], suite_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    step_env = env.copy()
    resolved: dict[str, str] = {}
    if not step.env_overrides:
        return step_env, resolved

    suite_tmp_dir = suite_dir.joinpath("runtime", step.key)
    for key, value in step.env_overrides:
        resolved_value = value
        if "{suite_tmp}" in resolved_value:
            suite_tmp_dir.mkdir(parents=True, exist_ok=True)
            resolved_value = resolved_value.replace("{suite_tmp}", str(suite_tmp_dir))
        step_env[key] = resolved_value
        resolved[key] = resolved_value
    return step_env, resolved


def _classify_status(*, exit_code: int, output: str, blocked_patterns: tuple[str, ...]) -> str:
    if exit_code == 0:
        return "PASS"
    lowered = output.lower()
    if any(pattern in lowered for pattern in blocked_patterns):
        return "BLOCKED"
    return "FAIL"


def _copy_artifacts(
    *,
    repo_root: Path,
    suite_dir: Path,
    latest_dir: Path,
    relative_paths: tuple[str, ...],
    latest_sync_warnings: list[dict],
) -> list[dict]:
    copied = []
    if not relative_paths:
        return copied
    artifacts_dir = suite_dir.joinpath("artifacts")
    latest_artifacts_dir = latest_dir.joinpath("artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    latest_artifacts_dir.mkdir(parents=True, exist_ok=True)
    for relative in relative_paths:
        source = repo_root.joinpath(relative)
        if not source.exists():
            continue
        destination = artifacts_dir.joinpath(source.name)
        latest_destination = latest_artifacts_dir.joinpath(source.name)
        shutil.copy2(source, destination)
        actual_latest_destination = _mirror_file_to_latest(
            source=source,
            latest_path=latest_destination,
            latest_sync_warnings=latest_sync_warnings,
            mirror_kind="artifact_copy",
        )
        copied.append(
            {
                "source": str(source),
                "suite_copy": str(destination),
                "latest_copy": str(actual_latest_destination),
            }
        )
    return copied


def _write_primary_suite_summary(*, summary: dict, suite_dir: Path) -> None:
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2)
    summary_md = _summary_markdown(summary)
    suite_dir.joinpath("summary.json").write_text(summary_json, encoding="utf-8")
    suite_dir.joinpath("summary.md").write_text(summary_md, encoding="utf-8")


def _write_suite_summary(*, summary: dict, suite_dir: Path, latest_dir: Path) -> list[dict]:
    warnings: list[dict] = []
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2)
    summary_md = _summary_markdown(summary)
    _write_primary_suite_summary(summary=summary, suite_dir=suite_dir)
    _mirror_text_to_latest(
        text=summary_json,
        latest_path=latest_dir.joinpath("summary.json"),
        latest_sync_warnings=warnings,
        mirror_kind="summary_json",
    )
    _mirror_text_to_latest(
        text=summary_md,
        latest_path=latest_dir.joinpath("summary.md"),
        latest_sync_warnings=warnings,
        mirror_kind="summary_markdown",
    )
    return warnings


def _mirror_text_to_latest(*, text: str, latest_path: Path, latest_sync_warnings: list[dict], mirror_kind: str) -> Path:
    try:
        latest_path.write_text(text, encoding="utf-8")
        return latest_path
    except PermissionError as exc:
        fallback_path = _fallback_latest_path(latest_path)
        fallback_path.write_text(text, encoding="utf-8")
        latest_sync_warnings.append(
            {
                "kind": mirror_kind,
                "requested_latest_path": str(latest_path),
                "fallback_latest_path": str(fallback_path),
                "error": str(exc),
                "status": "DEGRADED_LATEST_MIRROR",
            }
        )
        return fallback_path


def _mirror_file_to_latest(*, source: Path, latest_path: Path, latest_sync_warnings: list[dict], mirror_kind: str) -> Path:
    try:
        shutil.copy2(source, latest_path)
        return latest_path
    except PermissionError as exc:
        fallback_path = _fallback_latest_path(latest_path)
        shutil.copy2(source, fallback_path)
        latest_sync_warnings.append(
            {
                "kind": mirror_kind,
                "requested_latest_path": str(latest_path),
                "fallback_latest_path": str(fallback_path),
                "source_path": str(source),
                "error": str(exc),
                "status": "DEGRADED_LATEST_MIRROR",
            }
        )
        return fallback_path


def _fallback_latest_path(latest_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    return latest_path.with_name(f"{latest_path.stem}.fallback-{stamp}{latest_path.suffix}")


def _npm_executable() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _npx_executable() -> str:
    return "npx.cmd" if os.name == "nt" else "npx"


def _summary_markdown(summary: dict) -> str:
    lines = [
        f"# {summary['title']}",
        "",
        f"- command: `{summary['command_name']}`",
        f"- generated_at: `{summary['generated_at']}`",
        f"- overall_status: `{summary['overall_status']}`",
        f"- suite_dir: `{summary['suite_dir']}`",
        f"- latest_dir: `{summary['latest_dir']}`",
    ]
    if "axis_overall_status" in summary:
        lines.extend(
            [
                f"- axis_overall_status: `{summary['axis_overall_status']}`",
                "",
                "## Axis Summary",
                "",
                "| # | Axis | Status | Code | Test | Gate | Runtime |",
                "|---:|---|---|---|---|---|---|",
            ]
        )
        for axis in summary.get("axes", []):
            lines.append(
                f"| {axis['number']} | `{axis['title']}` | `{axis['status']}` | "
                f"`{axis['code_anchor']}` | `{axis['test_anchor']}` | `{axis['gate_anchor']}` | `{axis['runtime_anchor']}` |"
            )
            if axis["missing_step_keys"]:
                lines.append(f"|  | `missing-proof-steps` | `BLOCKED` | `{', '.join(axis['missing_step_keys'])}` |  |  |  |")
    lines.extend(["", "## Step Summary", "", "| Group | Step | Status | Exit |", "|---|---|---|---:|"])
    for step in summary["steps"]:
        lines.append(f"| `{step['group']}` | `{step['label']}` | `{step['status']}` | `{step['exit_code']}` |")
    if summary["artifacts"]:
        lines.extend(["", "## Copied Artifacts", ""])
        for artifact in summary["artifacts"]:
            lines.append(f"- `{artifact['source']}`")
    return "\n".join(lines) + "\n"
