"""
[AGRI-GUARDIAN] Triple Match Report
===================================
Generates a detailed reconciliation report comparing:
1. Physical Inventory (System stock levels)
2. Operational Records (Activities/Movements)
3. Financial Ledger (Accounting entries)

Run as: python manage.py triple_match_report [--farm FARM_CODE] [--export]
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from smart_agri.core.models import Farm
from smart_agri.inventory.models import ItemInventory, StockMovement
from smart_agri.finance.models import FinancialLedger


class Command(BaseCommand):
    help = '[AGRI-GUARDIAN] Generate Triple Match reconciliation report'

    def add_arguments(self, parser):
        parser.add_argument(
            '--farm',
            type=str,
            help='Specific farm code to report',
        )
        parser.add_argument(
            '--export',
            action='store_true',
            help='Export results to CSV',
        )
        parser.add_argument(
            '--tolerance',
            type=float,
            default=100.0,
            help='Variance tolerance in currency units (default: 100.0)',
        )

    def handle(self, *args, **options):
        farm_code = options.get('farm')
        export = options.get('export', False)
        tolerance = Decimal(str(options.get('tolerance', 100.0)))
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.WARNING('🔗 AGRI-GUARDIAN: Triple Match Reconciliation Report'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'Report Date: {date.today()}')
        self.stdout.write(f'Tolerance: {tolerance:,.2f} YER')
        self.stdout.write('=' * 80 + '\n')
        
        # Get farms to analyze
        farms = Farm.objects.all()
        if farm_code:
            farms = farms.filter(code=farm_code)
        
        if not farms.exists():
            self.stdout.write(self.style.ERROR('No farms found'))
            return
        
        report_data = []
        total_matched = 0
        total_variance = 0
        
        for farm in farms:
            self.stdout.write(f'\n📋 Farm: {farm.name}')
            self.stdout.write('-' * 60)
            
            # 1. INVENTORY: Current stock value
            inventory_qty = ItemInventory.objects.filter(
                farm=farm,
                deleted_at__isnull=True
            ).aggregate(total=Sum('qty'))['total'] or Decimal('0')
            
            # 2. OPERATIONS: Net stock movements
            movements_in = StockMovement.objects.filter(
                farm=farm,
                qty_delta__gt=0,
                deleted_at__isnull=True
            ).aggregate(total=Sum('qty_delta'))['total'] or Decimal('0')
            
            movements_out = StockMovement.objects.filter(
                farm=farm,
                qty_delta__lt=0,
                deleted_at__isnull=True
            ).aggregate(total=Sum('qty_delta'))['total'] or Decimal('0')
            
            movements_net = movements_in + movements_out  # out is negative
            
            # 3. FINANCE: Inventory Asset ledger balance
            ledger_debit = FinancialLedger.objects.filter(
                farm=farm,
                account_code__in=['1300-INV-ASSET', '1300']
            ).aggregate(total=Sum('debit'))['total'] or Decimal('0')
            
            ledger_credit = FinancialLedger.objects.filter(
                farm=farm,
                account_code__in=['1300-INV-ASSET', '1300']
            ).aggregate(total=Sum('credit'))['total'] or Decimal('0')
            
            ledger_balance = ledger_debit - ledger_credit
            
            # Calculate variances
            inv_ops_variance = inventory_qty - movements_net
            inv_fin_variance = inventory_qty - ledger_balance
            
            # Display results
            self.stdout.write(f'  📦 Inventory Qty:      {inventory_qty:>12,.2f}')
            self.stdout.write(f'  📊 Operations Net:     {movements_net:>12,.2f}')
            self.stdout.write(f'  💰 Ledger Balance:     {ledger_balance:>12,.2f}')
            self.stdout.write('')
            
            # Inventory vs Operations check
            if abs(inv_ops_variance) <= tolerance:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ Inventory ↔ Operations: MATCHED (Δ {inv_ops_variance:+,.2f})'
                ))
                total_matched += 1
            else:
                self.stdout.write(self.style.ERROR(
                    f'  ❌ Inventory ↔ Operations: MISMATCH (Δ {inv_ops_variance:+,.2f})'
                ))
                total_variance += 1
            
            # Inventory vs Finance check
            if abs(inv_fin_variance) <= tolerance:
                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ Inventory ↔ Finance:    MATCHED (Δ {inv_fin_variance:+,.2f})'
                ))
                total_matched += 1
            else:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️ Inventory ↔ Finance:    VARIANCE (Δ {inv_fin_variance:+,.2f})'
                ))
                total_variance += 1
            
            report_data.append({
                'farm': farm.name,
                'inventory_qty': inventory_qty,
                'movements_net': movements_net,
                'ledger_balance': ledger_balance,
                'inv_ops_variance': inv_ops_variance,
                'inv_fin_variance': inv_fin_variance,
            })
        
        # Summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.HTTP_INFO('📊 TRIPLE MATCH SUMMARY'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'  Farms analyzed: {len(report_data)}')
        self.stdout.write(f'  Matched pairs: {total_matched}')
        self.stdout.write(f'  Variances: {total_variance}')
        
        match_rate = (total_matched / (total_matched + total_variance) * 100) if (total_matched + total_variance) > 0 else 100
        
        if match_rate >= 90:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Triple Match Rate: {match_rate:.1f}%'))
        elif match_rate >= 70:
            self.stdout.write(self.style.WARNING(f'\n⚠️ Triple Match Rate: {match_rate:.1f}%'))
        else:
            self.stdout.write(self.style.ERROR(f'\n❌ Triple Match Rate: {match_rate:.1f}%'))
        
        if total_variance > 0:
            self.stdout.write(self.style.WARNING(
                '\n📝 NOTE: Variances may be due to:'
                '\n   - Pending ledger entries'
                '\n   - Activities not yet costed'
                '\n   - Timing differences (end-of-day sync)'
            ))
        
        self.stdout.write('')
