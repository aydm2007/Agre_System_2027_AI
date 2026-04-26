"""
Schema Sentinel - Nightly Integrity Check
AGRI-MAESTRO Phase 4: Automated Database Integrity Verification

Checks:
- Zombie tables (unmanaged by Django)
- Ghost triggers (hidden database logic)
- RLS enabled on critical tables
- Migration sync status
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, connections, DatabaseError, OperationalError
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = 'Runs nightly schema integrity checks for AGRI-MAESTRO compliance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Exit with error on any warning',
        )

    def handle(self, *args, **options):
        import logging
        from smart_agri.finance.services.financial_integrity_service import FinancialIntegrityService
        from smart_agri.core.services.inventory_service import InventoryService # Assuming we have similar check
        
        logger = logging.getLogger(__name__)
        strict_mode = options.get('strict', False)
        
        self.stdout.write(self.style.SUCCESS('🔍 AGRI-MAESTRO Schema & Data Sentinel'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        errors = []
        
        # --- PHASE 1: Schema Checks ---
        schema_checks = [
            ('Zombie Tables', self.check_zombie_tables),
            ('Ghost Triggers', self.check_ghost_triggers),
            ('RLS Enabled', self.check_rls_enabled),
            ('Migration Sync', self.check_migration_sync),
        ]
        
        for name, check_func in schema_checks:
            try:
                status, msg = check_func()
                if status == 'FAIL':
                    errors.append(f"[Schema] {name}: {msg}")
                    self.stdout.write(self.style.ERROR(f'❌ {name}: FAIL - {msg}'))
                elif status == 'WARN':
                    self.stdout.write(self.style.WARNING(f'⚠️  {name}: {msg}'))
                    if strict_mode: errors.append(f"[Schema Strict] {name}: {msg}")
                else:
                    self.stdout.write(self.style.SUCCESS(f'✅ {name}: PASS'))
            except (DatabaseError, OperationalError, RuntimeError) as e:
                errors.append(f"[Schema] {name} Crashed: {e}")
                logger.exception(f"Check {name} failed")

        # --- PHASE 2: Data Physics Checks ---
        self.stdout.write(self.style.SUCCESS('--- Checking Data Physics ---'))
        
        # Check 1: Financial Balance
        try:
            report = FinancialIntegrityService.verify_ledger_balance()
            if not report['is_balanced']:
                 errors.append(f"[Finance] Ledger Imbalance: {report['difference']}")
                 self.stdout.write(self.style.ERROR(f'❌ Financial Ledger: IMBALANCED'))
            else:
                 self.stdout.write(self.style.SUCCESS(f'✅ Financial Ledger: BALANCED'))
        except (DatabaseError, OperationalError, ValueError, RuntimeError) as e:
            errors.append(f"[Finance] Check Crashed: {e}")
            logger.exception("Financial balance check failed")

        # Check 2: Soft Deletions (Fix 30)
        try:
            soft_report = FinancialIntegrityService.check_illegal_deletions()
            if soft_report['status'] == 'FAIL':
                errors.append(f"[Finance] Illegal Deletions: {soft_report['count']}")
                self.stdout.write(self.style.ERROR(f"❌ Soft Deletions: FOUND {soft_report['count']}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"✅ Soft Deletions: CLEAN"))
        except (DatabaseError, OperationalError, ValueError, RuntimeError) as e:
             errors.append(f"[Finance] Soft Delete Check Crashed: {e}")
             logger.exception("Soft delete check failed")

        # Report Generation
        self.stdout.write(self.style.SUCCESS('=' * 60))
        if errors:
            self.stdout.write(self.style.WARNING(f"Found {len(errors)} issues during nightly check:"))
            for err in errors:
                logger.error(f"[NightlyAudit] {err}")
                self.stderr.write(self.style.ERROR(f" - {err}"))
            # We do NOT raise CommandError to allow pipeline to continue, unless strict
            if strict_mode:
                raise CommandError("Strict Mode: Integrity failures detected.")
        else:
            self.stdout.write(self.style.SUCCESS("🎉 All integrity checks passed!"))

    def check_zombie_tables(self):
        """Detect tables not managed by Django"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename LIKE 'core_%'
                AND tablename NOT IN (
                    'core_season'  -- Explicitly allowed unmanaged table
                )
            """)
            
            all_tables = {row[0] for row in cursor.fetchall()}
            
            # Get Django-managed tables
            from django.apps import apps
            managed_tables = set()
            for model in apps.get_models():
                if model._meta.app_label == 'core' and model._meta.managed:
                    managed_tables.add(model._meta.db_table)
            
            zombies = all_tables - managed_tables
            
            if zombies:
                return ('WARN', f'Found {len(zombies)} zombie tables: {zombies}')
            return ('PASS', None)

    def check_ghost_triggers(self):
        """Detect triggers doing hidden logic"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT trigger_name, event_object_table
                FROM information_schema.triggers
                WHERE trigger_schema = 'public'
                AND event_object_table LIKE 'core_%'
            """)
            triggers = cursor.fetchall()
            
            if triggers:
                trigger_list = [f"{t[0]} on {t[1]}" for t in triggers]
                return ('FAIL', f'Ghost triggers found: {trigger_list}')
            return ('PASS', None)

    def check_rls_enabled(self):
        """Verify RLS is enabled on critical tables"""
        critical_tables = [
            'core_farm',
            'core_location',
            'core_activity',
            'core_financialledger',
            'core_iteminventory',
            'core_stockmovement',
            'core_cropplan',
            'core_activitycostsnapshot',
            'core_auditlog',
        ]
        
        with connection.cursor() as cursor:
            missing_rls = []
            for table in critical_tables:
                cursor.execute("""
                    SELECT relrowsecurity 
                    FROM pg_class
                    WHERE relname = %s
                """, [table])
                result = cursor.fetchone()
                
                if not result or not result[0]:
                    missing_rls.append(table)
            
            if missing_rls:
                return ('FAIL', f'RLS not enabled on: {missing_rls}')
            
            # Check policy count
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pg_policies 
                WHERE schemaname = 'public'
            """)
            policy_count = cursor.fetchone()[0]
            
            if policy_count < 8:
                return ('WARN', f'Expected ≥8 RLS policies, found {policy_count}')
            
            return ('PASS', None)

    def check_migration_sync(self):
        """Verify all migrations applied"""
        executor = MigrationExecutor(connections['default'])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        if plan:
            unapplied = [f"{migration[0]}.{migration[1]}" for migration in plan]
            return ('FAIL', f'Unapplied migrations: {unapplied}')
        
        return ('PASS', None)


# Run with: python manage.py nightly_integrity_check
# Cron: 0 2 * * * cd /app && python manage.py nightly_integrity_check
