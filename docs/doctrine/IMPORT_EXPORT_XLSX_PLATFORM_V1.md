# Import / Export XLSX Platform v1

## Purpose

Define the first governed wave of the AgriAsset import/export platform for:

- advanced activity reports
- inventory reports
- inventory Excel imports
- planning Excel imports

This platform is mode-aware, backend-governed, and uses:

- `XLSX` as the primary business-facing format
- `JSON` as the optional technical/export format
- no `CSV` in the user-facing contract of this wave

## Core Contract

- The platform must reuse the existing truth chain and existing service-layer business logic.
- Export rendering, import parsing, preview, and file orchestration are platform concerns only.
- The platform must not create duplicate posting engines, duplicate truth tables, or route around existing inventory/report services.
- Business-facing files must be Arabic-first and RTL-first.
- Import preview and apply are separate stages. Upload alone must not write transactional rows.

## Export Contract

Each export job is represented by an async export request with:

- `export_type`
- `format`
- `template_code`
- `template_version`
- `farm_id`
- `mode_context`
- `filters`
- `locale`
- `rtl`

### First-wave export types

- `advanced_report`
- `inventory_balance`
- `inventory_movements`
- `inventory_low_stock`

### Output formats

- `xlsx`
- `json`

`XLSX` is the primary user-facing output. `JSON` is optional for integration, downstream analysis, or technical exchange.

## XLSX Workbook Standard

All user-facing workbooks in this platform must:

- render with sheet RTL enabled
- use Arabic headers
- include a readable Arabic cover sheet
- include freeze panes
- include autofilter
- use stable widths and table styling
- keep machine-readable metadata in a hidden `__meta` sheet when the workbook is a template or structured import file

The workbook generator must remain centralized so styling and metadata rules do not drift.

## Import Contract

All imports follow this lifecycle:

1. download server-issued template
2. upload `XLSX`
3. validate template metadata and structure
4. parse rows into preview payloads
5. validate business rules
6. present Arabic preview
7. apply via service layer only
8. return result summary and Arabic error workbook when needed

### Import job statuses

- `draft`
- `uploaded`
- `validated`
- `preview_ready`
- `approved_for_apply`
- `applied`
- `partially_rejected`
- `failed`

## Template Governance

Templates are server-issued and versioned.

Each template must include hidden metadata:

- `template_code`
- `template_version`
- `module`
- `farm_scope`
- `mode_scope`
- `generated_at`
- `checksum`

If metadata is missing or mismatched, the import must fail validation.

## Mode Governance

### SIMPLE

- may download `XLSX/JSON` exports subject to farm visibility and normal backend authorization
- may use operational inventory import templates only
- may use operational planning import templates only (`planning_master_schedule`, `planning_crop_plan_structure`)
- must not gain ledger authoring, governed finance mutation, or strict-only master-data powers through import

### STRICT

- may use operational inventory templates
- may use strict-only inventory templates for opening balance and item master work where policy allows
- may use operational planning templates plus `planning_crop_plan_budget`
- retains preview/apply governance and backend audit evidence

## First-Wave Templates

- `inventory_count_sheet`
- `inventory_operational_adjustment`
- `inventory_opening_balance`
- `inventory_item_master`
- `planning_master_schedule`
- `planning_crop_plan_structure`
- `planning_crop_plan_budget`

Interpretation:

- `inventory_count_sheet` and `inventory_operational_adjustment` are mode-aware operational templates
- `inventory_opening_balance` and `inventory_item_master` are `STRICT`-only
- `planning_master_schedule` and `planning_crop_plan_structure` are mode-aware operational templates
- `planning_crop_plan_budget` is `STRICT`-only and remains plan-scoped through `crop_plan_id` metadata

## Planning Import Wave

Planning imports are platform-governed and must not use authoritative client-side workbook parsing.

Supported planning templates:

- `planning_master_schedule`
  - farm-scoped seasonal/master planning rows
  - may create or update `CropPlan` and `CropPlanLocation`
- `planning_crop_plan_structure`
  - crop-plan-scoped operational structure rows
  - may create or update `PlannedActivity`
- `planning_crop_plan_budget`
  - crop-plan-scoped budget assumption rows
  - may create or update `CropPlanBudgetLine`
  - `STRICT` only

Planning rules:

- download is always server-issued and versioned
- `crop_plan_id` is required for structure/budget templates and is embedded in hidden `__meta`
- validation and preview happen in backend
- apply is idempotent and service-layer only
- failed rows return through an Arabic error workbook

## API Surface

The first-wave platform exposes unified endpoints for:

- export template discovery
- export job creation
- export job polling
- export download
- import template discovery
- import template download
- import upload
- import validation
- import preview
- import apply
- import error workbook download

The API contract is backend-authoritative. Frontend hiding alone is not sufficient governance.

## Evidence and Audit

- export job creation must leave traceable job metadata
- import upload, validation, and apply must leave audit evidence
- error workbooks are operational artifacts tied to the import job and must not silently replace audit evidence
- canonical score authority remains the latest `verify_axis_complete_v21` summary
- expanded browser or workflow bundles may be recorded as supplemental readiness evidence only

## Required Verification

When this platform changes, require at minimum:

```bash
python backend/manage.py test smart_agri.core.tests.test_import_export_platform smart_agri.core.tests.test_planning_import_platform --keepdb --noinput
npm --prefix frontend run test -- src/components/inventory/__tests__/InventoryImportExportCenter.test.jsx src/components/planning/__tests__/PlanningImportCenter.test.jsx src/pages/Reports/components/__tests__/DetailedTables.test.jsx --run
npm --prefix frontend run lint
python backend/manage.py verify_release_gate_v21
python backend/manage.py verify_axis_complete_v21
```

Supplemental inventory import/export E2E bundles may be attached when the platform wave expands, but they do not replace canonical release-gate authority.

## Wave 2 Report Registry

Wave 2 extends the same platform into a unified report catalog inside `Reports Hub`.

These export types are catalog-driven and must remain backend-authoritative:

- `daily_execution_summary`
- `daily_execution_detail`
- `plan_actual_variance`
- `perennial_tree_balance`
- `operational_readiness`

Each definition must expose registry metadata:

- `report_group`
- `mode_scope`
- `role_scope`
- `sensitivity_level`
- `default_column_profile`
- `allowed_formats`
- `ui_surface`

Wave 2 remains `XLSX` first, Arabic-first, RTL-first, with optional `JSON`.

## Wave 3 Governed Report Registry

Wave 3 adds heavier posture and governed reports while keeping the same platform contract:

- `inventory_expiry_batches`
- `fuel_posture_report`
- `fixed_asset_register`
- `contract_operations_posture`
- `supplier_settlement_posture`
- `petty_cash_posture`
- `receipts_deposit_posture`
- `governance_work_queue`

Design rules:

- use the same async export job contract
- use the same workbook generator
- keep reports read-side only
- do not create workflow-local export engines
- allow module-local dashboards to host export actions while the backend remains centralized

## UI Surface Contract

- `Reports Hub` owns the shared catalog for operational and analytical reports.
- `InventoryImportExportCenter` owns inventory template download, upload, preview, apply, and inventory report presets.
- `module_local` dashboards may expose small export centers for governed-heavy workflows such as fuel, fixed assets, contracts, supplier settlement, petty cash, receipts/deposit, and governance queues.

The UI must never become the authority for report availability. Availability and sensitivity remain backend-derived from the registry.

## Mode Governance for Wave 2 / Wave 3

### SIMPLE

- may export operational and posture-safe reports
- may access Wave 2 execution, variance, perennial, readiness, and operational inventory reports
- may access Wave 3 posture reports only when the same payload does not leak forbidden financial detail
- may not gain strict-only governance queues or master/governed imports

### STRICT

- may access the full Wave 2 catalog
- may access governed-heavy Wave 3 exports according to role scope
- keeps inventory imports under preview/apply governance

## Registry and History Expectations

The platform must expose:

- export template discovery with report metadata
- import template discovery with mode-aware filtering
- export job history
- import job history

History panels are operational trace surfaces. They do not replace canonical runtime evidence, but they must remain queryable and user-visible.
