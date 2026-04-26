"""
[AGRI-GUARDIAN] Migration 0067: RLS policies for SyncConflictDLQ.

[Axis 6] Tenant Isolation: Row-Level Security for the offline
sync conflict dead letter queue. Uses the established session-based
pattern: current_setting('app.current_user_id').
"""
from django.db import migrations


RLS_UP = """
-- Enable RLS on core_syncconflict_dlq
ALTER TABLE core_syncconflict_dlq ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see conflicts for their own farm
CREATE POLICY syncconflict_dlq_farm_isolation ON core_syncconflict_dlq
    USING (farm_id IN (
        SELECT farm_id FROM accounts_farmmembership
        WHERE user_id = current_setting('app.current_user_id', true)::int
    ));
"""

RLS_DOWN = """
DROP POLICY IF EXISTS syncconflict_dlq_farm_isolation ON core_syncconflict_dlq;
ALTER TABLE core_syncconflict_dlq DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0066_syncconflict_dlq'),
    ]

    operations = [
        migrations.RunSQL(sql=RLS_UP, reverse_sql=RLS_DOWN),
    ]
