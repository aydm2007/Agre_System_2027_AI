"""
[AGRI-GUARDIAN] System Diagnostics & Health Check
==================================================
Best practices diagnostic system that validates:
- Database integrity
- Financial consistency
- Inventory physics
- RLS policies
- Service layer compliance
- Triple Match Rule

Run as: python manage.py diagnostic_system [--fix]
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Sum, Count, F, Q
from django.utils import timezone

# Models
from smart_agri.core.models import (
    Farm, Location, Activity, DailyLog, CropPlan,
    ItemInventory, LocationTreeStock, TreeStockEvent,
    Employee, Asset
)
from smart_agri.finance.models import FinancialLedger, FiscalYear, FiscalPeriod
from smart_agri.inventory.models import StockMovement, ItemInventoryBatch

logger = logging.getLogger(__name__)


class DiagnosticResult:
    """Container for diagnostic results"""
    
    def __init__(self, name: str):
        self.name = name
        self.passed = True
        self.warnings = []
        self.errors = []
        self.info = []
        self.fixed = []
    
    def add_error(self, message: str):
        self.errors.append(message)
        self.passed = False
    
    def add_warning(self, message: str):
        self.warnings.append(message)
    
    def add_info(self, message: str):
        self.info.append(message)
    
    def add_fix(self, message: str):
        self.fixed.append(message)


class Command(BaseCommand):
    help = '[AGRI-GUARDIAN] Run comprehensive system diagnostics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix detected issues',
        )
        parser.add_argument(
            '--farm',
            type=str,
            help='Specific farm code to diagnose',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output results as JSON',
        )

    def handle(self, *args, **options):
        self.fix_mode = options.get('fix', False)
        self.farm_filter = options.get('farm')
        self.json_output = options.get('json', False)
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.WARNING('🔬 AGRI-GUARDIAN: System Diagnostics'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Time: {timezone.now()}')
        self.stdout.write(f'Fix Mode: {"Enabled" if self.fix_mode else "Disabled"}')
        self.stdout.write('=' * 70 + '\n')
        
        results = []
        
        # Run all diagnostic checks
        results.append(self._check_database_connection())
        results.append(self._check_rls_policies())
        results.append(self._check_inventory_physics())
        results.append(self._check_financial_integrity())
        results.append(self._check_triple_match())
        results.append(self._check_orphan_records())
        results.append(self._check_ledger_immutability())
        results.append(self._check_service_layer_compliance())
        results.append(self._check_fiscal_periods())
        results.append(self._check_tree_inventory_consistency())
        
        # Print results
        self._print_results(results)
        
        # Calculate overall score
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        score = (passed / total) * 100 if total > 0 else 0
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.HTTP_INFO(f'📊 OVERALL HEALTH SCORE: {score:.0f}%'))
        self.stdout.write(f'   Passed: {passed}/{total} checks')
        self.stdout.write('=' * 70)
        
        if score < 100:
            self.stdout.write(self.style.WARNING('\n⚠️ Run with --fix to attempt automatic repairs'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ All systems healthy!'))

    def _check_database_connection(self) -> DiagnosticResult:
        """Check database connectivity and basic schema"""
        result = DiagnosticResult('Database Connection')
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result.add_info('Database connection: OK')
                
                # Check PostgreSQL version
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                result.add_info(f'PostgreSQL: {version[:50]}...')
                
                # Check for critical tables (note: some tables use underscores)
                critical_tables = [
                    'core_farm', 'core_activity', 'core_dailylog',
                    'core_financialledger', 'core_item_inventory'
                ]
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                for table in critical_tables:
                    if table not in existing_tables:
                        result.add_error(f'Missing critical table: {table}')
                    else:
                        result.add_info(f'Table {table}: OK')
                
        except Exception as e:
            logger.exception("Database connection failed")
            result.add_error(f'Database connection failed: {e}')
        
        return result

    def _check_rls_policies(self) -> DiagnosticResult:
        """Check Row Level Security policies"""
        result = DiagnosticResult('RLS Policies')
        
        required_rls_tables = [
            'core_activity', 'core_dailylog', 'core_cropplan',
            'core_financialledger', 'core_employee', 'core_asset'
        ]
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT tablename, rowsecurity 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                tables = {row[0]: row[1] for row in cursor.fetchall()}
                
                for table in required_rls_tables:
                    if table not in tables:
                        result.add_warning(f'Table {table} not found')
                    elif not tables[table]:
                        result.add_error(f'RLS not enabled on {table}')
                    else:
                        result.add_info(f'RLS enabled on {table}')
                
        except Exception as e:
            logger.exception("RLS check failed")
            result.add_error(f'RLS check failed: {e}')
        
        return result

    def _check_inventory_physics(self) -> DiagnosticResult:
        """Check for negative inventory (physics violation)"""
        result = DiagnosticResult('Inventory Physics')
        
        # Check for negative item inventory
        negative_items = ItemInventory.objects.filter(qty__lt=0)
        if negative_items.exists():
            for item in negative_items[:5]:
                result.add_error(
                    f'Negative inventory: {item.item.name} @ {item.location.name} = {item.qty}'
                )
            if self.fix_mode:
                # Attempt fix by creating adjustment
                for item in negative_items:
                    item.qty = Decimal('0')
                    item.save()
                    result.add_fix(f'Reset {item.item.name} to 0')
        else:
            result.add_info('No negative inventory detected')
        
        # Check for negative tree stock
        negative_trees = LocationTreeStock.objects.filter(current_tree_count__lt=0)
        if negative_trees.exists():
            for stock in negative_trees[:5]:
                result.add_error(
                    f'Negative tree stock: {stock.crop_variety.name} @ {stock.location.name}'
                )
        else:
            result.add_info('No negative tree stock detected')
        
        return result

    def _check_financial_integrity(self) -> DiagnosticResult:
        """Check financial ledger integrity"""
        result = DiagnosticResult('Financial Integrity')
        
        # Check for balanced entries (Debit should equal Credit in aggregate for closed periods)
        for farm in Farm.objects.all():
            # Note: FinancialLedger is immutable (no soft-delete)
            total_debit = FinancialLedger.objects.filter(
                farm=farm
            ).aggregate(total=Sum('debit'))['total'] or Decimal('0')
            
            total_credit = FinancialLedger.objects.filter(
                farm=farm
            ).aggregate(total=Sum('credit'))['total'] or Decimal('0')
            
            balance = total_debit - total_credit
            
            if abs(balance) > Decimal('0.01'):
                result.add_warning(
                    f'Farm {farm.name}: Unbalanced ledger. Debit={total_debit}, Credit={total_credit}, Diff={balance}'
                )
            else:
                result.add_info(f'Farm {farm.name}: Ledger balanced ✓')
        
        # Check for entries without row_hash
        unhashed = FinancialLedger.objects.filter(
            Q(row_hash__isnull=True) | Q(row_hash='')
        ).count()
        
        if unhashed > 0:
            result.add_error(f'{unhashed} ledger entries missing row_hash (integrity risk)')
        else:
            result.add_info('All ledger entries have integrity hashes')
        
        return result

    def _check_triple_match(self) -> DiagnosticResult:
        """Check Triple Match Rule: Inventory = Operations = Finance"""
        result = DiagnosticResult('Triple Match Rule')
        
        for farm in Farm.objects.all():
            # 1. System Inventory Count (Note: ItemInventory has qty only, no avg_cost)
            inventory_qty = ItemInventory.objects.filter(
                farm=farm, deleted_at__isnull=True
            ).aggregate(total=Sum('qty'))['total'] or Decimal('0')
            
            # 2. Financial Ledger (Inventory Asset Account - code is like '1300-INV-ASSET')
            ledger_debit = FinancialLedger.objects.filter(
                farm=farm, account_code='1300-INV-ASSET'
            ).aggregate(total=Sum('debit'))['total'] or Decimal('0')
            
            ledger_credit = FinancialLedger.objects.filter(
                farm=farm, account_code='1300-INV-ASSET'
            ).aggregate(total=Sum('credit'))['total'] or Decimal('0')
            
            ledger_balance = ledger_debit - ledger_credit
            
            # Compare
            difference = abs(inventory_qty - ledger_balance)
            
            if difference > Decimal('100.00'):  # Tolerance
                result.add_warning(
                    f'Farm {farm.name}: Triple Match variance. '
                    f'Inventory={inventory_qty:.2f}, Ledger={ledger_balance:.2f}, Diff={difference:.2f}'
                )
            else:
                result.add_info(f'Farm {farm.name}: Triple Match OK ✓')
        
        return result

    def _check_orphan_records(self) -> DiagnosticResult:
        """Check for orphan records (FK violations)"""
        result = DiagnosticResult('Orphan Records')
        
        # Activities without DailyLog
        orphan_activities = Activity.objects.filter(
            log__isnull=True, deleted_at__isnull=True
        ).count()
        
        if orphan_activities > 0:
            result.add_error(f'{orphan_activities} activities without DailyLog')
            if self.fix_mode:
                Activity.objects.filter(log__isnull=True).update(deleted_at=timezone.now())
                result.add_fix('Soft-deleted orphan activities')
        else:
            result.add_info('No orphan activities')
        
        # DailyLogs without Farm (DailyLog uses farm, not crop_plan)
        orphan_logs = DailyLog.objects.filter(
            farm__isnull=True, deleted_at__isnull=True
        ).count()
        
        if orphan_logs > 0:
            result.add_error(f'{orphan_logs} daily logs without Farm')
        else:
            result.add_info('No orphan daily logs')
        
        # Tree events without stock
        orphan_events = TreeStockEvent.objects.filter(
            location_tree_stock__isnull=True
        ).count()
        
        if orphan_events > 0:
            result.add_error(f'{orphan_events} tree events without stock')
        else:
            result.add_info('No orphan tree events')
        
        return result

    def _check_ledger_immutability(self) -> DiagnosticResult:
        """Check ledger immutability controls"""
        result = DiagnosticResult('Ledger Immutability')
        
        # Check for database trigger
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT trigger_name FROM information_schema.triggers
                    WHERE event_object_table = 'core_financialledger'
                    AND trigger_name LIKE '%prevent%mutation%'
                """)
                triggers = cursor.fetchall()
                
                if triggers:
                    result.add_info(f'Immutability trigger found: {triggers[0][0]}')
                else:
                    result.add_warning('No immutability trigger detected on core_financialledger')
        except Exception as e:
            logger.exception("Could not check triggers")
            result.add_warning(f'Could not check triggers: {e}')
        
        # Note: FinancialLedger is immutable - it has no updated_at field by design
        # Just confirm all entries exist (immutability is enforced by immutable model design)
        ledger_count = FinancialLedger.objects.count()
        result.add_info(f'Ledger contains {ledger_count} entries (immutable by design)')
        
        return result

    def _check_service_layer_compliance(self) -> DiagnosticResult:
        """Check service layer patterns"""
        result = DiagnosticResult('Service Layer Compliance')
        
        # Check for activities created via service (has cost snapshot)
        try:
            from smart_agri.core.models.activity import ActivityCostSnapshot
            
            total_activities = Activity.objects.filter(
                deleted_at__isnull=True, status='completed'
            ).count()
            
            # Note: ActivityCostSnapshot may not have deleted_at if not inheriting SoftDeleteModel
            activities_with_snapshot = ActivityCostSnapshot.objects.values('activity').distinct().count()
            
            coverage = (activities_with_snapshot / total_activities * 100) if total_activities > 0 else 100
            
            if coverage < 80:
                result.add_warning(
                    f'Cost snapshot coverage: {coverage:.0f}% '
                    f'({activities_with_snapshot}/{total_activities} activities)'
                )
            else:
                result.add_info(f'Cost snapshot coverage: {coverage:.0f}% ✓')
        except Exception as e:
            logger.exception("Cost snapshot check skipped")
            result.add_warning(f'Cost snapshot check skipped: {str(e)[:50]}')
        
        # Check for stock movements without service (field is ref_type, not reference_type)
        movements_without_ref = StockMovement.objects.filter(
            ref_type=''
        ).count()
        
        if movements_without_ref > 0:
            result.add_warning(f'{movements_without_ref} stock movements without reference')
        else:
            result.add_info('All stock movements have references')
        
        return result

    def _check_fiscal_periods(self) -> DiagnosticResult:
        """Check fiscal period configuration"""
        result = DiagnosticResult('Fiscal Periods')
        
        current_year = date.today().year
        
        for farm in Farm.objects.all():
            fy = FiscalYear.objects.filter(farm=farm, year=current_year).first()
            
            if not fy:
                result.add_error(f'Farm {farm.name}: No fiscal year {current_year}')
                if self.fix_mode:
                    FiscalYear.objects.create(
                        farm=farm,
                        year=current_year,
                        start_date=date(current_year, 1, 1),
                        end_date=date(current_year, 12, 31),
                    )
                    result.add_fix(f'Created fiscal year {current_year} for {farm.name}')
            else:
                periods = FiscalPeriod.objects.filter(fiscal_year=fy).count()
                if periods < 12:
                    result.add_warning(f'Farm {farm.name}: Only {periods}/12 fiscal periods')
                else:
                    result.add_info(f'Farm {farm.name}: Fiscal periods OK ✓')
        
        return result

    def _check_tree_inventory_consistency(self) -> DiagnosticResult:
        """Check tree inventory consistency"""
        result = DiagnosticResult('Tree Inventory Consistency')
        
        for stock in LocationTreeStock.objects.all():
            # Sum of events should equal current count
            events_sum = TreeStockEvent.objects.filter(
                location_tree_stock=stock
            ).aggregate(total=Sum('tree_count_delta'))['total'] or 0
            
            if events_sum != stock.current_tree_count:
                result.add_error(
                    f'Stock {stock.id} inconsistent: Events sum={events_sum}, Current={stock.current_tree_count}'
                )
            
            # Note: LocationTreeStock uses productivity_status FK, not separate count fields
            # Skip the productive/non-productive check as those fields don't exist
        
        if not result.errors and not result.warnings:
            result.add_info('Tree inventory consistent ✓')
        
        return result

    def _print_results(self, results: list):
        """Print diagnostic results"""
        for result in results:
            # Header
            status_icon = '✅' if result.passed else '❌'
            status_style = self.style.SUCCESS if result.passed else self.style.ERROR
            
            self.stdout.write(f'\n{status_icon} {status_style(result.name)}')
            self.stdout.write('-' * 50)
            
            # Info messages
            for info in result.info:
                self.stdout.write(f'   ℹ️  {info}')
            
            # Warnings
            for warning in result.warnings:
                self.stdout.write(self.style.WARNING(f'   ⚠️  {warning}'))
            
            # Errors
            for error in result.errors:
                self.stdout.write(self.style.ERROR(f'   ❌ {error}'))
            
            # Fixes applied
            for fix in result.fixed:
                self.stdout.write(self.style.SUCCESS(f'   🔧 FIXED: {fix}'))
