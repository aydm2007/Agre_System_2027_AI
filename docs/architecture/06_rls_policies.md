
# 🛡️ Architecture: Row Level Security (RLS)
**Last Updated:** 2026-02-03
**Status:** Live (Phase 3)

## 🎯 Purpose
To enforce **Multi-Tenancy** at the database layer.
Previously, tenant isolation relied entirely on Django's ORM `filter(farm_id=...)`. A single developer mistake could leak data between farms.

## 🏗️ Implementation
We use PostgreSQL **Row Level Security** Policies.
- **Enforcement:** Database Kernel level.
- **Bypass:** Only Superusers (or migrations) can bypass RLS.
- **Context:** The `current_user_id` or `current_farm_id` is set via session variables.

## 📜 Policies Defined (`0007_add_rls_policies.py`)

### 1. Farm Isolation
Users can ONLY see data belonging to their assigned Farm.
```sql
CREATE POLICY farm_isolation ON core_activity
USING (farm_id = current_setting('app.current_farm_id')::bigint);
```

### 2. User Privacy
Users can ONLY see their own sensitive profile data.
```sql
CREATE POLICY user_privacy ON core_employee
USING (user_id = current_setting('app.current_user_id')::bigint);
```

### 3. Public Data
Some reference tables (e.g., `Unit`, `Crop`) are readable by all authenticated users but writable only by Superusers.

## ⚠️ Developer Impact
- **Testing:** Tests must mimic a logged-in user context or they will see empty querysets.
- **Migrations:** Run as Superuser (bypass RLS by default).
- **Raw SQL:** Must manually set `app.current_farm_id` if bypassing ORM middleware.
