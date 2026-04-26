from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0056_locationirrigationpolicy_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                INSERT INTO core_location_irrigation_policy
                    (is_active, created_at, updated_at, deleted_at, zakat_rule, valid_daterange, approved_at, reason, approved_by_id, deleted_by_id, location_id)
                SELECT
                    TRUE,
                    NOW(),
                    NOW(),
                    NULL,
                    CASE
                        WHEN f.zakat_rule = '10_PERCENT' THEN 'RAIN_10'
                        ELSE 'WELL_5'
                    END AS zakat_rule,
                    daterange(DATE '2000-01-01', NULL, '[)') AS valid_daterange,
                    NOW() AS approved_at,
                    'Backfill from Farm.zakat_rule migration 0057',
                    NULL,
                    NULL,
                    l.id
                FROM core_location l
                INNER JOIN core_farm f ON f.id = l.farm_id
                WHERE l.deleted_at IS NULL
                  AND NOT EXISTS (
                    SELECT 1
                    FROM core_location_irrigation_policy p
                    WHERE p.location_id = l.id
                      AND p.deleted_at IS NULL
                  );
            """,
            reverse_sql="""
                DELETE FROM core_location_irrigation_policy
                WHERE reason = 'Backfill from Farm.zakat_rule migration 0057';
            """,
        )
    ]

