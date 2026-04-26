# Phase 0 — Baseline Verification Report

**Scope:** Establish a baseline inventory of mutation endpoints, farm-scope enforcement paths, idempotency coverage, and float usage hot spots before Phase 1 hardening.

**Inputs Reviewed**
- Core API router registrations for business endpoints (`backend/smart_agri/core/api/router.py`).
- Idempotency mixin and farm-scoped permission implementation (`backend/smart_agri/core/api/viewsets/base.py`, `backend/smart_agri/core/api/permissions.py`).
- Finance and sales API surfaces (`backend/smart_agri/finance/api.py`, `backend/smart_agri/finance/api_advances.py`, `backend/smart_agri/sales/api.py`).
- Mutation-centric viewsets in core modules (`backend/smart_agri/core/api/viewsets/*.py`, `backend/smart_agri/core/api/activities.py`).
- Decimal enforcement and float guardrails (`backend/smart_agri/core/services/costing.py`, `backend/smart_agri/core/api/utils.py`).

---

## 1) Mutation Endpoint Inventory (Baseline)

> **Method:** Enumerated router registrations and viewsets with create/update actions. This list focuses on the endpoints that can mutate state (POST/PUT/PATCH/DELETE or custom actions).

### Core Router-Registered Mutation Endpoints
- **Farms / Locations / Assets**: `FarmViewSet`, `LocationViewSet`, `AssetViewSet` (Asset uses idempotent create).【F:backend/smart_agri/core/api/viewsets/farm.py†L25-L130】【F:backend/smart_agri/core/api/router.py†L34-L57】
- **Crops / Farm Crops / Tasks / Crop Products / Crop Materials**: `CropViewSet`, `FarmCropViewSet`, `TaskViewSet`, `CropProductViewSet`, `CropMaterialViewSet`.【F:backend/smart_agri/core/api/viewsets/crop.py†L29-L304】【F:backend/smart_agri/core/api/router.py†L38-L63】
- **Planning**: `CropPlanViewSet`, `CropPlanBudgetLineViewSet`, `PlannedActivityViewSet`, `PlannedMaterialViewSet`.【F:backend/smart_agri/core/api/viewsets/planning.py†L8-L38】【F:backend/smart_agri/core/api/router.py†L66-L70】
- **Logs & Activities**: `DailyLogViewSet`, `AttachmentViewSet`, `ActivityViewSet` (idempotent create).【F:backend/smart_agri/core/api/viewsets/log.py†L35-L90】【F:backend/smart_agri/core/api/activities.py†L15-L50】【F:backend/smart_agri/core/api/router.py†L43-L47】
- **Inventory**: `ItemViewSet`, `ItemInventoryViewSet`, `HarvestLotViewSet` (idempotent create on inventory + harvest lots).【F:backend/smart_agri/core/api/viewsets/inventory.py†L37-L260】【F:backend/smart_agri/core/api/router.py†L49-L55】
- **HR**: `EmployeeViewSet`, `EmploymentContractViewSet`, `TimesheetViewSet`.【F:backend/smart_agri/core/api/hr.py†L118-L181】【F:backend/smart_agri/core/api/hr.py†L225-L227】
- **Sync**: `SyncRecordViewSet` (mutations for sync tracking).【F:backend/smart_agri/core/api/viewsets/log.py†L276-L320】【F:backend/smart_agri/core/api/router.py†L59-L60】

### Finance + Sales Mutation Endpoints
- **Sales invoices**: `SalesInvoiceViewSet` (idempotent create + custom actions).【F:backend/smart_agri/sales/api.py†L7-L186】
- **Fiscal periods**: `FiscalPeriodViewSet` (idempotent create + close/soft-close actions).【F:backend/smart_agri/finance/api.py†L146-L240】
- **Actual expenses**: `ActualExpenseViewSet` (idempotent create).【F:backend/smart_agri/finance/api.py†L273-L360】
- **Worker advances**: `WorkerAdvanceViewSet` (idempotent create).【F:backend/smart_agri/finance/api_advances.py†L9-L60】

---

## 2) Farm-Scope Enforcement Matrix (Baseline)

> **Method:** Reviewed permission classes and farm access filters; noted reliance on `FarmScopedPermission` and explicit farm filters within querysets.

### Farm-Scoped Permission Defaults
- `AuditedModelViewSet` enforces `FarmScopedPermission` for all non-safe methods (POST/PUT/PATCH/DELETE).【F:backend/smart_agri/core/api/viewsets/base.py†L15-L60】
- `FarmScopedPermission` resolves farm access via `FarmMembership` with a fallback path when farm context is not explicit (potentially leaky for non-nested endpoints).【F:backend/smart_agri/core/api/permissions.py†L29-L96】

### ViewSets with Explicit Farm Filtering
- `FinancialLedgerViewSet` applies farm scoping across direct farm_id and activity relations; supports `farm` query param filter with multi-path joins (direct farm + crop plan + log).【F:backend/smart_agri/finance/api.py†L58-L132】
- `FiscalYearViewSet` and `FiscalPeriodViewSet` filter by allowed farm IDs from `user_farm_ids` when user is not superuser.【F:backend/smart_agri/finance/api.py†L134-L211】

### ViewSets Without `FarmScopedPermission`
- Finance viewsets use `IsAuthenticated` directly (not `FarmScopedPermission`), relying on explicit queryset filtering for farm isolation rather than permission enforcement.【F:backend/smart_agri/finance/api.py†L54-L211】
- Accounts viewsets in `accounts/api.py` use `viewsets.ModelViewSet` (no farm-scoped permission). This should be reviewed for tenant governance where applicable.【F:backend/smart_agri/accounts/api.py†L209-L592】

**Baseline Gap Note:** Non-nested endpoints without explicit farm filters depend on fallback role checks in `FarmScopedPermission`, which can allow broader access than intended when farm context is missing.【F:backend/smart_agri/core/api/permissions.py†L64-L96】

---

## 3) Idempotency Enforcement Coverage (Baseline)

> **Method:** Enumerated usage of `IdempotentCreateMixin` and custom idempotency enforcement calls.

### Endpoints With Idempotent Create Mixin
- Core activities & logs: `ActivityViewSet`, `DailyLogViewSet`, `AttachmentViewSet`.【F:backend/smart_agri/core/api/activities.py†L15-L50】【F:backend/smart_agri/core/api/viewsets/log.py†L35-L90】
- Inventory: `ItemInventoryViewSet`, `HarvestLotViewSet`.【F:backend/smart_agri/core/api/viewsets/inventory.py†L37-L260】
- Farm assets: `AssetViewSet`.【F:backend/smart_agri/core/api/viewsets/farm.py†L25-L80】
- Finance: `FiscalPeriodViewSet`, `ActualExpenseViewSet`, `WorkerAdvanceViewSet`.【F:backend/smart_agri/finance/api.py†L146-L360】【F:backend/smart_agri/finance/api_advances.py†L9-L60】
- Sales: `SalesInvoiceViewSet` uses idempotent create mixin and explicit idempotency on custom actions.【F:backend/smart_agri/sales/api.py†L7-L176】

### Endpoints Without Idempotent Create Mixin (Potential Gaps)
- Core create endpoints in crops/planning/inventory masters (e.g., `CropViewSet`, `TaskViewSet`, `CropPlanViewSet`, `ItemViewSet`) are currently on `AuditedModelViewSet` without explicit idempotency enforcement.【F:backend/smart_agri/core/api/viewsets/crop.py†L29-L304】【F:backend/smart_agri/core/api/viewsets/planning.py†L8-L31】【F:backend/smart_agri/core/api/viewsets/inventory.py†L37-L110】
- HR endpoints (employees/contracts/timesheets) use `ModelViewSet` without idempotency mixin.【F:backend/smart_agri/core/api/hr.py†L118-L181】

**Baseline Gap Note:** Idempotency is enforced for several financial and inventory mutation endpoints, but not consistently across all core creation endpoints. Phase 2 should extend enforcement to all mutation routes that can impact inventory/finance/operational records.

---

## 4) Float Usage / Decimal Compliance Scan (Baseline)

> **Method:** `rg` scan for float usage across backend services and API utilities.

### Guardrails Already Present
- `to_decimal` in `costing.py` explicitly rejects float inputs for financial integrity and enforces Decimal usage with strict errors.【F:backend/smart_agri/core/services/costing.py†L21-L49】
- `_safe_float` is explicitly forbidden in API utilities; `_safe_decimal` is preferred for numeric parsing.【F:backend/smart_agri/core/api/utils.py†L62-L90】

### Known Float Touchpoints
- Management commands accept float CLI args (e.g., BOM deviation, triple match threshold). These are operational tools, not direct financial mutation paths, but should be kept isolated from writes or converted to Decimal prior to persistence in later phases.【F:backend/smart_agri/core/management/commands/check_bom_deviation.py†L35-L52】【F:backend/smart_agri/core/management/commands/triple_match_report.py†L34-L50】
- Tests cast Decimal fields to float for assertions; these are not production paths but indicate areas for future tightening in Phase 3 compliance checks.【F:backend/smart_agri/core/tests/test_activity_items.py†L60-L120】【F:backend/smart_agri/sales/tests/test_invoice_printing.py†L53-L61】

---

## 5) Phase 0 Deliverables (Completed)

- ✅ Mutation endpoint inventory (above).
- ✅ Farm-scope enforcement baseline with gap notes (above).
- ✅ Idempotency coverage baseline (above).
- ✅ Float/Decimal scan notes (above).

---

## 6) Immediate Follow-Up (Feeds Phase 1)

1) **Add explicit farm filters** for any viewsets lacking concrete farm context (especially non-nested endpoints relying on fallback role checks).【F:backend/smart_agri/core/api/permissions.py†L64-L96】
2) **Expand idempotency enforcement** for all mutation endpoints that can alter inventory or financial records beyond current coverage.【F:backend/smart_agri/core/api/viewsets/base.py†L65-L162】
3) **Confirm finance endpoints use `transaction.atomic()` + `select_for_update()`** in service-layer mutations (especially for stock/ledger paths) before Phase 2 hardening.

