from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum, F
from smart_agri.core.models import Farm
from smart_agri.inventory.models import ItemInventory
from smart_agri.finance.models import FinancialLedger

class Command(BaseCommand):
    help = '[AUDIT_MODE] Forensic Valuation Reconciliation: Physical Stock vs Ledger Account 1300'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- [AUDIT_MODE] Forensic Valuation Report ---\n"))
        
        farms = Farm.objects.all()
        overall_delta = Decimal("0")

        for farm in farms:
            # 1. Physical Valuation
            # Sum of (Inventory.qty * Item.unit_price)
            physical_data = ItemInventory.objects.filter(farm=farm).select_related('item').all()
            physical_valuation = sum((inv.qty * inv.item.unit_price for inv in physical_data), Decimal("0"))
            
            # 2. Ledger Valuation
            # Sum of (Debit - Credit) for account 1300
            ledger_balance = FinancialLedger.objects.filter(
                farm=farm, 
                account_code=FinancialLedger.ACCOUNT_INVENTORY_ASSET
            ).aggregate(
                balance=Sum(F('debit') - F('credit'))
            )['balance'] or Decimal("0")
            
            delta = physical_valuation - ledger_balance
            overall_delta += delta
            
            status_style = self.style.SUCCESS if abs(delta) < 1 else self.style.WARNING
            
            self.stdout.write(f"Farm: {farm.name}")
            self.stdout.write(f"  - Physical Valuation: {physical_valuation:,.2f} YER")
            self.stdout.write(f"  - Ledger Balance (1300): {ledger_balance:,.2f} YER")
            self.stdout.write(status_style(f"  - Variance: {delta:,.2f} YER"))
            self.stdout.write("-" * 40)

        if abs(overall_delta) < 1:
            self.stdout.write(self.style.SUCCESS(f"\n✅ RECONCILIATION SUCCESS: Overall System Delta is {overall_delta:,.2f}"))
        else:
            self.stdout.write(self.style.ERROR(f"\n🚨 RECONCILIATION FAILURE: Overall System Delta is {overall_delta:,.2f}"))
        
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- End of Report ---\n"))
