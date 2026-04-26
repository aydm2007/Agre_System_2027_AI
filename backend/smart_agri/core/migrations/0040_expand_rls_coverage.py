# [AGRI-GUARDIAN] Expand RLS to missing critical tables
# Forensic Audit: Tables containing financial/HR/operational data
# must be protected by Row Level Security for tenant isolation.
from django.db import migrations


MISSING_RLS_TABLES = [
    'core_dailylog',
    'core_employee',
    'core_employmentcontract',
    'core_timesheet',
    'core_payrollrun',
    'core_payrollslip',
    'core_auditlog',
    'core_syncrecord',
    'core_harvestlog',
    'core_fuelconsumptionalert',
    'core_activitycostsnapshot',
    'core_activityemployee',
]


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return  # Skip on SQLite
    with schema_editor.connection.cursor() as cursor:
        for table in MISSING_RLS_TABLES:
            cursor.execute("SELECT to_regclass(%s)", [table])
            if cursor.fetchone()[0]:
                schema_editor.execute(
                    f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;'
                )
                schema_editor.execute(
                    f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY;'
                )


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        for table in MISSING_RLS_TABLES:
            cursor.execute("SELECT to_regclass(%s)", [table])
            if cursor.fetchone()[0]:
                schema_editor.execute(
                    f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;'
                )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_rls_policies_location_cropplan'),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
