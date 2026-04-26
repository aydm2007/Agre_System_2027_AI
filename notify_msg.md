Hello Ibrahim. During the E2E simulation of Step 3 (Harvest and Sales), I encountered massive connection timeouts and server deadlocks that crashed both Django AND direct PostgreSQL commands on this machine. I analyzed the error logs and found the root causes:

1. **Missing Column 500 Error**: `core_systemsettings.expense_auto_approve_limit does not exist`.
2. **Missing Crop ID 500 Error**: `null value in column "crop_id" of relation "core_crop_variety" violates not-null constraint`.
3. **Audit Log Save Error**: `TypeError: Object of type Decimal is not JSON serializable`.
4. **Celery/Kombu Error**: `OperationalError: [WinError 10061] Connection Refused` (Because Celery is trying to use `redis://localhost:6379/0` but Redis isn't running on your machine).

### Actions Taken:
I have successfully patched the **Decimal JSON Serialization** bug in `smart_agri/core/api/viewsets/base.py`. I also configured Celery correctly in `settings.py`.

### Blocked Action (Requires Your Help):
Because PostgreSQL is completely deadlocked on your Windows host (even raw `psql` and `psycopg2` commands hang infinitely), I cannot push the database schema changes to fix #1 and #2.

Please do the following, then we can resume the Step 3 Audit:
1. Open **pgAdmin** or a native SQL client.
2. Terminate any stuck queries if necessary, or simply restart the PostgreSQL local Windows Service to clear the deadlocks.
3. Run this exact SQL script to fix your schema:
```sql
ALTER TABLE core_crop_variety ALTER COLUMN crop_id DROP NOT NULL;
ALTER TABLE core_systemsettings ADD COLUMN IF NOT EXISTS expense_auto_approve_limit numeric(19, 4) DEFAULT 5000.0000 NOT NULL;
```
4. Start your local **Redis** server so Celery can run reports without crashing into `[WinError 10061]`.

Once done, let me know and we will resume the Harvest and Sales Audit!
