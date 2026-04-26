"""
Schema Sentinel: Zombie Table Detection Script
AGRI-GUARDIAN: Database Hygiene Enforcement

This script detects:
1. Zombie Tables - Tables in DB but not in Django models
2. Ghost Tables - Django models missing from DB
3. Orphan Sequences - Unused sequences

Usage:
    python manage.py shell < scripts/detect_zombies.py
"""
import logging
from django.apps import apps
from django.db import connection

logger = logging.getLogger(__name__)

# Tables managed by Django that should be excluded from zombie detection
DJANGO_SYSTEM_TABLES = {
    'django_migrations',
    'django_session', 
    'django_content_type',
    'django_admin_log',
    'auth_group',
    'auth_group_permissions',
    'auth_permission',
    'auth_user',
    'auth_user_groups',
    'auth_user_user_permissions',
}

# Known extensions and materialized views (not zombie tables)
KNOWN_EXTENSIONS = {
    'view_farm_dashboard_stats',   # Materialized view — FarmDashboardStats proxy
    'finance_audit_log_finance',   # [AGRI-GUARDIAN] Unmanaged shadow ledger — created by SQL trigger
                                   # See: finance/models.py:FinanceAuditLog (managed=False)
                                   # Maintained by SQL patch, NOT Django. Must NOT be dropped.
}


def get_django_table_names():
    """Get all table names registered in Django models."""
    tables = set()
    for model in apps.get_models():
        tables.add(model._meta.db_table)
    return tables


def get_database_table_names():
    """Get all table names from the database."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        return {row[0] for row in cursor.fetchall()}


def get_database_views():
    """Get all views and materialized views from the database."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT viewname FROM pg_views WHERE schemaname = 'public'
            UNION
            SELECT matviewname FROM pg_matviews WHERE schemaname = 'public'
        """)
        return {row[0] for row in cursor.fetchall()}


def detect_zombie_tables():
    """
    Detect zombie tables - tables in DB but not in Django models.
    These might be leftover from previous migrations or typos.
    """
    django_tables = get_django_table_names()
    db_tables = get_database_table_names()
    db_views = get_database_views()
    
    # Zombies = DB tables - Django tables - System tables - Known extensions - Views
    all_valid = django_tables | DJANGO_SYSTEM_TABLES | KNOWN_EXTENSIONS | db_views
    zombies = db_tables - all_valid
    
    return list(zombies)


def detect_ghost_tables():
    """
    Detect ghost tables - Django models without DB tables.
    These need migrations to be created.
    """
    django_tables = get_django_table_names()
    db_tables = get_database_table_names()
    db_views = get_database_views()
    
    ghosts = django_tables - db_tables - db_views
    return list(ghosts)


def detect_orphan_sequences():
    """
    Detect sequences that are not owned by any column.
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT s.relname AS sequence_name
            FROM pg_class s
            JOIN pg_namespace n ON n.oid = s.relnamespace
            WHERE s.relkind = 'S'
            AND n.nspname = 'public'
            AND NOT EXISTS (
                SELECT 1 FROM pg_depend d
                WHERE d.objid = s.oid
                AND d.deptype = 'a'
            )
        """)
        return [row[0] for row in cursor.fetchall()]


def check_duplicate_sequences():
    """
    Check for suspiciously named duplicate sequences.
    Example: core_laborrate_id_seq AND core_laborrate_id_seq1
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT relname 
            FROM pg_class 
            WHERE relkind = 'S' 
            AND relnamespace = 'public'::regnamespace
            ORDER BY relname
        """)
        sequences = [row[0] for row in cursor.fetchall()]
    
    duplicates = []
    for i, seq in enumerate(sequences):
        # Check if there's a sequence with same name + number suffix
        if seq.endswith('1') or seq.endswith('2'):
            base_name = seq.rstrip('0123456789')
            if base_name in sequences:
                duplicates.append((base_name, seq))
    
    return duplicates


def run_audit():
    """Run full schema audit and print report."""
    print("\n" + "="*60)
    print("🛡️ AGRI-GUARDIAN SCHEMA SENTINEL REPORT")
    print("="*60 + "\n")
    
    # Zombie Tables
    zombies = detect_zombie_tables()
    print(f"🧟 ZOMBIE TABLES ({len(zombies)} found):")
    if zombies:
        for z in sorted(zombies):
            print(f"   ⚠️  {z}")
        print("   Action: Verify if needed, otherwise DROP TABLE")
    else:
        print("   ✅ No zombie tables detected")
    print()
    
    # Ghost Tables
    ghosts = detect_ghost_tables()
    print(f"👻 GHOST TABLES ({len(ghosts)} found):")
    if ghosts:
        for g in sorted(ghosts):
            print(f"   ⚠️  {g}")
        print("   Action: Run makemigrations and migrate")
    else:
        print("   ✅ No ghost tables detected")
    print()
    
    # Duplicate Sequences
    duplicates = check_duplicate_sequences()
    print(f"🔁 DUPLICATE SEQUENCES ({len(duplicates)} found):")
    if duplicates:
        for base, dup in duplicates:
            print(f"   ⚠️  {base} <-> {dup}")
        print("   Action: Drop the duplicate, keep the original")
    else:
        print("   ✅ No duplicate sequences detected")
    print()
    
    # Summary
    total_issues = len(zombies) + len(ghosts) + len(duplicates)
    print("="*60)
    if total_issues == 0:
        print("✅ SCHEMA HEALTH: EXCELLENT - No issues detected")
    else:
        print(f"⚠️  SCHEMA HEALTH: {total_issues} issue(s) require attention")
    print("="*60 + "\n")
    
    return {
        'zombies': zombies,
        'ghosts': ghosts,
        'duplicate_sequences': duplicates,
        'total_issues': total_issues
    }


if __name__ == '__main__':
    # When run as script
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
    django.setup()
    run_audit()
