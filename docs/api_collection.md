# AgriAsset V21 API Collection
## Postman / cURL Examples

> Reference class: public compatibility examples.
> This file is not a higher-order canonical source than `PRD V21`, `AGENTS.md`, doctrine, or the
> latest closure evidence. Update practical examples when public contracts change.
>
> Path policy:
> - auth and health live under `/api/`
> - business endpoints live under `/api/v1/`

**Base URL**: `http://localhost:8000/api`  
**التاريخ**: 2026-01-02  
**الإصدار**: 2.0 Gold Level  

---

## Authentication

### 1. Login (الحصول على Token)
```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin@example.com",
    "password": "your_password"
  }'
```

**Response**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**استخدام Token في الطلبات اللاحقة**:
```bash
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/farms/
```

---

## Farms (المزارع)

### 2. Get All Farms
```bash
curl -X GET http://localhost:8000/api/v1/farms/ \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Create Farm
```bash
curl -X POST http://localhost:8000/api/v1/farms/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "مزرعة النخيل",
    "city": "المدينة المنورة",
    "area_ha": 75.5,
    "currency": "SAR"
  }'
```

### 4. Get Farm by ID
```bash
curl -X GET http://localhost:8000/api/v1/farms/1/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## Locations (المواقع)

### 5. Get Locations for a Farm
```bash
curl -X GET "http://localhost:8000/api/v1/locations/?farm=1" \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Create Location
```bash
curl -X POST http://localhost:8000/api/v1/locations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "farm": 1,
    "name": "القطعة الشمالية",
    "planted_area": 5000.0,
    "planted_uom": "m2"
  }'
```

---

## Crop Plans (الخطط الزراعية)

### 7. Get Active Crop Plans
```bash
curl -X GET "http://localhost:8000/api/v1/crop-plans/?status=active" \
  -H "Authorization: Bearer $TOKEN"
```

### 8. Create Crop Plan
```bash
curl -X POST http://localhost:8000/api/v1/crop-plans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "farm": 1,
    "crop": 2,
    "location": 3,
    "name": "خطة الطماطم - ربيع 2026",
    "start_date": "2026-02-01",
    "end_date": "2026-06-30",
    "budget_materials": 25000.00,
    "budget_labor": 15000.00,
    "budget_machinery": 10000.00,
    "budget_total": 50000.00,
    "currency": "SAR",
    "status": "active"
  }'
```

---

## Daily Logs & Activities

### 9. Create Daily Log
```bash
curl -X POST http://localhost:8000/api/v1/daily-logs/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "log_date": "2026-01-02",
    "farm": 1,
    "supervisor": "أحمد محمد",
    "notes": "يوم عمل عادي"
  }'
```

### 10. Create Activity
```bash
curl -X POST http://localhost:8000/api/v1/activities/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "log": 15,
    "task": 3,
    "crop_plan": 5,
    "location": 2,
    "hours": 6.0,
    "planted_area": 3000.0,
    "planted_uom": "m2",
    "notes": "ري الصباح"
  }'
```

---

## Reports (التقارير)

### 11. Advanced Report (Conservative Direct GET)
```bash
curl -X GET "http://localhost:8000/api/v1/advanced-report/?start=2026-01-01&end=2026-01-31&farm=1" \
  -H "Authorization: Bearer $TOKEN"
```

**With Conservative Tree Filters**:
```bash
curl -X GET "http://localhost:8000/api/v1/advanced-report/?start=2026-01-01&end=2026-01-31&farm=1&location_id=4&variety_id=3&status_code=productive&include_tree_inventory=true" \
  -H "Authorization: Bearer $TOKEN"
```

**With Explicit Section Scope**:
```bash
curl -X GET "http://localhost:8000/api/v1/advanced-report/?start=2026-01-01&end=2026-01-31&farm_id=1&section_scope=summary&section_scope=activities&section_scope=detailed_tables" \
  -H "Authorization: Bearer $TOKEN"
```

### 11B. Advanced Report Async Job
```bash
curl -X POST "http://localhost:8000/api/v1/advanced-report/requests/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start": "2026-01-01",
    "end": "2026-01-31",
    "farm_id": "1",
    "section_scope": ["summary", "activities", "detailed_tables"]
  }'
```

---

### 12. Financial Risk Zone (Gold Level) 🆕

```bash
curl -X GET "http://localhost:8000/api/v1/reports/financial-risk-zone/?farm=1&crop_id=2" \
  -H "Authorization: Bearer $TOKEN"
```

**Response Example**:
```json
[
  {
    "activity_id": 234,
    "task_name": "تسميد",
    "date": "2026-01-15",
    "cost_total": 4850.0000,
    "mean": 1650.0000,
    "threshold": 2980.0000,
    "deviation": 3200.0000,
    "risk_score": 3.42
  },
  {
    "activity_id": 256,
    "task_name": "ري",
    "date": "2026-01-20",
    "cost_total": 3500.0000,
    "mean": 1650.0000,
    "threshold": 2980.0000,
    "deviation": 1850.0000,
    "risk_score": 2.35
  }
]
```

**Interpretation**:
- `activity_id: 234` has `risk_score: 3.42` → **high alert** (مراجعة فورية)
- `activity_id: 256` has `risk_score: 2.35` → **warning** (تحذير)

---

### 13. Export to Excel
```bash
curl -X GET "http://localhost:8000/api/v1/reports/export-excel/?start=2026-01-01&end=2026-01-31&farm=1" \
  -H "Authorization: Bearer $TOKEN" \
  --output report_2026-01.xlsx
```

---

## Inventory (المخزون)

### 14. Get Inventory Balances
```bash
curl -X GET http://localhost:8000/api/v1/item-inventories/ \
  -H "Authorization: Bearer $TOKEN"
```

### 15. Create Stock Movement (In)
```bash
curl -X POST http://localhost:8000/api/v1/stock-ledger/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item": 8,
    "movement_type": "in",
    "qty": 200.0,
    "movement_date": "2026-01-02",
    "reference": "PO-2026-001",
    "notes": "شراء من المورد ABC"
  }'
```

### 16. Create Stock Movement (Out)
```bash
curl -X POST http://localhost:8000/api/v1/stock-ledger/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "item": 8,
    "movement_type": "out",
    "qty": 50.0,
    "movement_date": "2026-01-02",
    "reference": "Activity-#234",
    "notes": "استخدام في نشاط الري"
  }'
```

---

## Tree Inventory (الأشجار المعمرة)

### 17. Get Tree Stocks
```bash
curl -X GET "http://localhost:8000/api/v1/tree-inventory/summary/?location=1" \
  -H "Authorization: Bearer $TOKEN"
```

### 18. Create Tree Event (Planting)
```bash
curl -X POST http://localhost:8000/api/v1/tree-inventory/events/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location_tree_stock": 12,
    "event_type": "planting",
    "tree_count_delta": 100,
    "event_timestamp": "2026-01-02T09:00:00Z",
    "planting_date": "2026-01-02",
    "seedling_source": "مشتل المدينة",
    "notes": "زراعة دفعة جديدة من النخيل"
  }'
```

### 19. Create Tree Event (Harvest)
```bash
curl -X POST http://localhost:8000/api/v1/tree-inventory/events/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location_tree_stock": 12,
    "event_type": "harvest",
    "tree_count_delta": 0,
    "event_timestamp": "2026-01-02T14:00:00Z",
    "harvest_quantity": 250.5,
    "harvest_uom": "kg",
    "notes": "حصاد التمر الأول"
  }'
```

### 20. Create Tree Event (Loss)
```bash
curl -X POST http://localhost:8000/api/v1/tree-inventory/events/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location_tree_stock": 12,
    "event_type": "loss",
    "tree_count_delta": -5,
    "event_timestamp": "2026-01-02T16:00:00Z",
    "tree_loss_reason": 3,
    "notes": "فقدان بسبب الجفاف"
  }'
```

---

## Postman Collection JSON

يمكنك استيراد المجموعة التالية في Postman:

```json
{
  "info": {
    "name": "AgriAsset V21 API Collection",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"admin@example.com\",\n  \"password\": \"your_password\"\n}"
            },
            "url": {
              "raw": "{{base_url}}/token/",
              "host": ["{{base_url}}"],
              "path": ["token", ""]
            }
          }
        }
      ]
    },
    {
      "name": "Reports",
      "item": [
        {
          "name": "Financial Risk Zone (Gold)",
          "request": {
            "method": "GET",
            "header": [{"key": "Authorization", "value": "Bearer {{token}}"}],
            "url": {
              "raw": "{{base_url}}/reports/financial-risk-zone/?farm=1&crop_id=2",
              "host": ["{{base_url}}"],
              "path": ["reports", "financial-risk-zone", ""],
              "query": [
                {"key": "farm", "value": "1"},
                {"key": "crop_id", "value": "2"}
              ]
            }
          }
        }
      ]
    }
  ],
  "variable": [
    {"key": "base_url", "value": "http://localhost:8000/api"},
    {"key": "token", "value": ""}
  ]
}
```

---

## Environment Variables (Postman)

```json
{
  "id": "agriasset-dev",
  "name": "AgriAsset Development",
  "values": [
    {"key": "base_url", "value": "http://localhost:8000/api", "enabled": true},
    {"key": "token", "value": "", "enabled": true}
  ]
}
```

**بعد Login**: انسخ `access` token والصقه في متغير `token` في Postman Environment.

---

## Testing Checklist

- [ ] Login and get token
- [ ] Create farm
- [ ] Create location
- [ ] Create crop plan with budget
- [ ] Create daily log
- [ ] Create activities with costs
- [ ] Test Financial Risk Zone API
- [ ] Verify anomalies detected
- [ ] Export Excel report
- [ ] Test offline sync (if PWA enabled)

---

**نهاية API Collection**
