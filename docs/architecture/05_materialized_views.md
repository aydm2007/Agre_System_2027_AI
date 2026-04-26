
# 🚀 Architecture: Materialized Views (Performance Layer)
**Last Updated:** 2026-02-03
**Status:** Live (Phase 3)

## 🎯 Purpose
To resolve the O(N) performance bottleneck in the Farm Dashboard.
Previously, calculating "Total Stock Value" or "Burn Rate" required Python to iterate over every Inventory Item and Contract in the database, leading to 5-10s load times for large farms.

## 🏗️ Implementation
We use PostgreSQL **Materialized Views** to pre-calculate complex aggregations.
- **View Name:** `view_farm_dashboard_stats`
- **Refresh Strategy:** On-Demand (Triggered by Admin or Scheduled Task).
- **Access Speed:** O(1) (Indexed Lookup by `farm_id`).

## 📊 Schema Definition
Defined in Migration `0009_create_dashboard_view.py`.

```sql
CREATE MATERIALIZED VIEW view_farm_dashboard_stats AS
SELECT
    f.id AS farm_id,
    COALESCE(emp_stats.headcount, 0) AS headcount,
    COALESCE(emp_stats.burn_rate, 0) AS monthly_burn_rate,
    (SELECT COUNT(*) FROM core_cropplan ...) AS active_plans,
    (SELECT COALESCE(SUM(inv.qty * item.unit_price), 0) ...) AS total_stock_value,
    NOW() AS last_refreshed_at
FROM core_farm f
LEFT JOIN (...)
```

## 🔄 Refresh Mechanism
The view is exposed via a Read-Only Django Model: `core.models.views.FarmDashboardStats`.

```python
# To Refresh:
from django.db import connection
cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY view_farm_dashboard_stats;")
```

## 🛡️ "Ghost Table" Incident
During implementation, `core_employee` and `core_employmentcontract` were found missing.
- **Resolution:** Manually restored via `0008_restore_ghost_tables.py` using original SQL definitions.
