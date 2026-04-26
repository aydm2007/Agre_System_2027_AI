# 🏗️ هندسة نظام AgriAsset 2025

## الملخص التنفيذي
نظام إدارة الأصول الزراعية المتكامل يدير المزارع، المحاصيل، المخزون، والتكاليف.

---

## 📐 الهيكل المعماري

```mermaid
graph TB
    subgraph Frontend["🖥️ Frontend (React)"]
        UI[React Components]
        API[API Client]
        Farm[Farm Context]
    end
    
    subgraph Backend["⚙️ Django Backend"]
        Views[REST Views]
        Services[Service Layer]
        Models[Django Models]
    end
    
    subgraph Data["💾 PostgreSQL"]
        DB[(Database)]
        RLS[Row Level Security]
    end
    
    UI --> API
    API --> Views
    Views --> Services
    Services --> Models
    Models --> DB
    DB --> RLS
```

---

## 🔒 طبقة الأمان (RLS)

```mermaid
flowchart LR
    U[User] --> M[Middleware]
    M --> |app.user_id| P[Policy Check]
    P --> |farm_id ∈ memberships| D[Data Access]
```

### السياسات المطبقة:
- `financialledger_farm_isolation`
- `activity_isolation`
- `cropplan_isolation`
- `inventory_isolation`

---

## 💰 تدفق المنطق المالي

```mermaid
sequenceDiagram
    participant A as Activity
    participant C as Costing Service
    participant L as Financial Ledger
    
    A->>C: calculate_activity_cost()
    C->>C: Lock with select_for_update()
    C->>C: Calculate (Decimal only)
    C->>L: Create Immutable Snapshot
    L-->>A: Cost updated
```

---

## 📁 هيكل المجلدات

```
backend/
├── smart_agri/
│   ├── core/
│   │   ├── models/      # 14 نموذج
│   │   ├── services/    # 26 خدمة
│   │   ├── api/         # REST endpoints
│   │   └── tests/       # 45 ملف اختبار
│   └── accounts/        # إدارة المستخدمين
└── migrations/          # 95 هجرة

frontend/
├── src/
│   ├── api/generated/   # API المولد
│   ├── components/      # 19 مكون
│   └── pages/          # 30 صفحة
└── dist/               # البناء النهائي
```

---

## 🧠 الخدمات الحرجة (The Brain)

| الخدمة | الوظيفة | الحماية |
|--------|---------|---------|
| `costing.py` | حساب التكاليف | `STRICT_MODE=True` |
| `tree_inventory.py` | مخزون الأشجار | `select_for_update` |
| `cost_allocation.py` | توزيع التكاليف | `Decimal` only |

---

**آخر تحديث:** 2026-01-28
