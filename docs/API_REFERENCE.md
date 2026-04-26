# AgriAsset V21 API Reference

> Reference class: public API guide.
> Canonical product and execution truth still come from `PRD V21`, `AGENTS.md`, doctrine, and the
> latest canonical evidence under `docs/evidence/closure/latest/`.
>
> Path policy:
> - infrastructure endpoints such as auth, health, and schema live under `/api/`
> - application business routers live under `/api/v1/`

## Authentication
All authenticated endpoints require `Authorization: Bearer <token>` header.

### Login
```
POST /api/auth/token/
Body: { "username": "...", "password": "..." }
Response: { "access": "...", "refresh": "..." }
```

### Refresh Token
```
POST /api/auth/refresh/
Body: { "refresh": "..." }
Response: { "access": "..." }
```

### Health & Schema
```
GET /api/health/
GET /api/health/live/
GET /api/health/ready/
GET /api/schema/
GET /api/docs/
```

---

## System Mode
```
GET /api/v1/system-mode/
Auth: AllowAny (public)
Response: { "strict_erp_mode": true/false }
```

---

## Core Endpoints

### Farms
```
GET    /api/v1/farms/              # List all farms (tenant-scoped)
POST   /api/v1/farms/              # Create farm
GET    /api/v1/farms/:id/          # Farm detail
PATCH  /api/v1/farms/:id/          # Update farm
```

### Daily Logs
```
GET    /api/v1/daily-logs/         # List logs (farm_id filter required)
POST   /api/v1/daily-logs/         # Create daily log
Headers: X-Idempotency-Key: <uuid>   # MANDATORY for mutations
```

### Crop Plans
```
GET    /api/v1/crop-plans/         # List plans
POST   /api/v1/crop-plans/         # Create plan
GET    /api/v1/crop-plans/:id/     # Plan detail with tasks
```

---

## Financial Endpoints (Strict Mode / Finance Leader)

### Fiscal Periods
```
GET    /api/v1/fiscal-years/                # List fiscal years (farm-scoped)
GET    /api/v1/fiscal-periods/              # List periods (farm + year filter)
POST   /api/v1/fiscal-periods/:id/close/    # Close period (soft → hard)
Headers: X-Idempotency-Key: <uuid>
```

### Financial Ledger
```
GET    /api/v1/financial-ledger/            # List entries (farm-scoped)
POST   /api/v1/financial-ledger/            # Manual journal entry
Headers: X-Idempotency-Key: <uuid>
Filters: farm_id, period, cost_center, crop_plan
```

### IAS 41 Revaluation
```
POST   /api/v1/financial-ledger/ias41-revalue/   # @idempotent
Body: { "farm_id": 1, "fair_value_per_unit": "150.00" }
Headers: X-Idempotency-Key: <uuid>
```

### Expenses
```
GET    /api/v1/expenses/                    # List expenses (farm-scoped)
POST   /api/v1/expenses/                    # Create expense
Headers: X-Idempotency-Key: <uuid>
```

---

## Sales Endpoints

### Sales
```
GET    /api/v1/sales/                       # List sales (farm-scoped)
POST   /api/v1/sales/                       # Create sale
POST   /api/v1/sales/:id/confirm/           # Confirm sale (validates minimum price)
Headers: X-Idempotency-Key: <uuid>
```

### Customers
```
GET    /api/v1/customers/                   # List customers
POST   /api/v1/customers/                   # Create customer
```

---

## Inventory Endpoints

### Stock Management
```
GET    /api/v1/stock-movements/             # List movements (farm-scoped)
POST   /api/v1/stock-movements/             # Record movement
Headers: X-Idempotency-Key: <uuid>
```

### Items
```
GET    /api/v1/items/                       # List items
POST   /api/v1/items/                       # Create item
```

---

## Reports & Audit

### Advanced Report (Direct GET + Async)
```
GET    /api/v1/advanced-report/             # Conservative direct payload
Filters: start, end, farm|farm_id, season|season_id, crop_id, task_id, location|location_id,
         include_tree_inventory, section_scope
Notes:
- direct GET without explicit section_scope returns a usable payload with summary + details
- explicit section_scope enables sectional optimization
- include_tree_inventory may be used with either conservative or sectional loading
```

Contract table:

| Case | Expected behavior |
|------|-------------------|
| direct GET without explicit `section_scope` | returns usable `summary + details` |
| GET with explicit `section_scope=summary` | returns summary-only payload and omits details rows |
| GET with explicit detail sections | returns summary plus paginated details |
| async POST job | uses the same filter semantics but returns a job record instead of inline payload |

Response shape highlights:
```json
{
  "summary": { "...": "..." },
  "details": [{ "...": "..." }],
  "details_meta": {
    "returned": 1,
    "limit": 50,
    "offset": 0,
    "has_more": false,
    "total": 1
  },
  "section_scope": ["summary"]
}
```

### Advanced Report (Async Job)
```
POST   /api/v1/advanced-report/requests/    # Submit async report job
GET    /api/v1/advanced-report/requests/:id/ # Check job status
Response: { "status": "PENDING|COMPLETED|FAILED", "result_url": "..." }
```

### Audit Log (Read-Only)
```
GET    /api/v1/audit-logs/                  # List audit entries (farm-scoped)
Filters: farm_id, action, model, actor_name, date range
```

---

## Headers Reference

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |
| `X-Idempotency-Key` | For mutations | UUID v4, client-generated |
| `Content-Type` | Yes | `application/json` |
| `Accept-Language` | Optional | `ar` (default) or `en` |

## Error Response Format

All errors follow this unified format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "الرسالة بالعربي",
    "details": { "field_name": ["خطأ محدد"] }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|:-----------:|-------------|
| `VALIDATION_ERROR` | 400 | خطأ في المدخلات |
| `AUTHENTICATION_FAILED` | 401 | فشل التحقق من الهوية |
| `PERMISSION_DENIED` | 403 | ليس لديك صلاحية |
| `NOT_FOUND` | 404 | العنصر غير موجود |
| `THROTTLED` | 429 | تجاوز الحد المسموح |
| `IDEMPOTENCY_REPLAY` | 200 | تم تنفيذ الطلب مسبقاً |
| `FISCAL_PERIOD_CLOSED` | 400 | الفترة المالية مغلقة |
| `INSUFFICIENT_STOCK` | 400 | الرصيد غير كافي |
| `DECIMAL_REQUIRED` | 400 | القيمة العشرية مطلوبة |
| `INTERNAL_ERROR` | 500 | خطأ داخلي |
