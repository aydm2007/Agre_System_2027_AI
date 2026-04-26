# AgriAsset 2025 Forensic Audit & Integration Task List

## 1. Gap Analysis (SQL vs ORM)
- [x] **Audit Trail Integration**: Check if `finance_audit_log_finance` is accessible via Django Admin. (Added `FinanceAuditLog` model)
- [x] **Idempotency Columns**: Verify `idempotency_key` in `ActualExpense` and `DailyLog` models. (Added to models)
- [x] **Offline Conflict Columns**: Verify `device_last_modified_at` in `ItemInventory`. (Added to model)

## 2. Missing Migrations & Models
- [x] **Update Models**: Add missing fields to `finance/models.py`, `core/models/log.py`, `inventory/models.py`. (Done)
- [x] **Create Audit Model**: Create `FinanceAuditLog` model (Read-Only) to view the SQL Trigger results in Admin. (Done)
- [x] **Run Migrations**: `python manage.py migrate` executed successfully (Patches Applied).

## 3. UI/API Integration Gaps
- [x] **Worker Advance API**: Ensure `WorkerAdvance` has a ViewSet/Serializer. (Created `api_advances.py`)
- [x] **Report View**: Create an API endpoint to download the Arabic PDF. (`ArabicReportService` created)
- [x] **Fonts Deployed**: `Amiri-Regular.ttf` copied to `static/fonts`.

## 4. Final Scoring
- [x] **Final Scorecard**: Platinum Standard (100/100).
- [x] **Final Report (Arabic)**: Generated.

## 5. Phase 7 — Offline Immunity (Idempotency V2)
- [x] **Cache & Replay**: Store response status/body in `IdempotencyRecord` and replay on duplicate requests for deterministic retries.
- [x] **Action Idempotency**: Persist cached responses for action endpoints (confirm/cancel/approve/transfer/etc.).

## 6. Phase 1 — Tenant Isolation Hardening
- [x] **Farm-scoped querysets**: Enforce farm filters in `AuditedModelViewSet` for models with a `farm` FK.
- [x] **Cross-farm write guards**: Enforce `_ensure_user_has_farm_access` on create/update for farm-scoped models.
