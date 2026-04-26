from django.db import migrations


CREATE_M2M_SQL = """
CREATE TABLE IF NOT EXISTS core_crop_supported_tasks (
    id BIGSERIAL PRIMARY KEY,
    crop_id BIGINT NOT NULL REFERENCES core_crop(id) ON DELETE CASCADE,
    task_id BIGINT NOT NULL REFERENCES core_task(id) ON DELETE CASCADE,
    UNIQUE (crop_id, task_id)
);
CREATE INDEX IF NOT EXISTS core_crop_supported_tasks_crop_id_idx
    ON core_crop_supported_tasks (crop_id);
CREATE INDEX IF NOT EXISTS core_crop_supported_tasks_task_id_idx
    ON core_crop_supported_tasks (task_id);
"""


BACKFILL_SQL = """
INSERT INTO core_crop_supported_tasks (crop_id, task_id)
SELECT t.crop_id, t.id
FROM core_task t
JOIN core_crop c ON c.id = t.crop_id
WHERE t.deleted_at IS NULL
  AND c.deleted_at IS NULL
ON CONFLICT (crop_id, task_id) DO NOTHING;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0058_alter_activityemployee_unique_together_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_M2M_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql=BACKFILL_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
