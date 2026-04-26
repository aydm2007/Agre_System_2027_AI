from django.db.models import Sum, Q
from decimal import Decimal
from smart_agri.finance.models import FinancialLedger

class FinancialReportService:
    def __init__(self, farm):
        self.farm = farm

    def get_trial_balance(self):
        """ميزان المراجعة بناءً على سجل الأستاذ العام"""
        # Group by account_code and sum debits/credits
        data = FinancialLedger.objects.filter(farm=self.farm).values('account_code').annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        
        report = []
        for entry in data:
            code = entry['account_code']
            debit = entry['total_debit'] or Decimal('0')
            credit = entry['total_credit'] or Decimal('0')
            balance = debit - credit
            
            report.append({
                'account_code': code,
                'account_name': dict(FinancialLedger.ACCOUNT_CHOICES).get(code, code),
                'debit': debit,
                'credit': credit,
                'balance': balance
            })
        return report

    def get_profit_and_loss(self, from_date=None, to_date=None):
        """تقرير الأرباح والخسائر"""
        query = Q(farm=self.farm)
        if from_date:
            query &= Q(created_at__date__gte=from_date) # FinancialLedger uses created_at
        if to_date:
            query &= Q(created_at__date__lte=to_date)

        # Revenue accounts (start with 5)
        revenue_total = FinancialLedger.objects.filter(
            query, 
            account_code=FinancialLedger.ACCOUNT_SALES_REVENUE
        ).aggregate(total=Sum('credit'))['total'] or Decimal('0')
        
        # Expense accounts (start with 10, 20, 30, 40, 60, 70)
        expense_accounts = [
            FinancialLedger.ACCOUNT_LABOR,
            FinancialLedger.ACCOUNT_MATERIAL,
            FinancialLedger.ACCOUNT_MACHINERY,
            FinancialLedger.ACCOUNT_OVERHEAD,
            FinancialLedger.ACCOUNT_COGS,
            FinancialLedger.ACCOUNT_FUEL_EXPENSE,
            FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
            FinancialLedger.ACCOUNT_WASTAGE_EXPENSE,
        ]
        expenses_total = FinancialLedger.objects.filter(
            query, 
            account_code__in=expense_accounts
        ).aggregate(total=Sum('debit'))['total'] or Decimal('0')
        
        return {
            'revenue': revenue_total,
            'expenses': expenses_total,
            'net_profit': revenue_total - expenses_total
        }

    def get_balance_sheet(self):
        """الميزانية العمومية"""
        # Asset Accounts
        assets = [
            FinancialLedger.ACCOUNT_CASH_ON_HAND,
            FinancialLedger.ACCOUNT_BANK,
            FinancialLedger.ACCOUNT_RECEIVABLE,
            FinancialLedger.ACCOUNT_INVENTORY_ASSET,
            FinancialLedger.ACCOUNT_WIP,
            FinancialLedger.ACCOUNT_FIXED_ASSET,
            FinancialLedger.ACCOUNT_FUEL_INVENTORY,
        ]
        
        # Liability Accounts
        liabilities = [
            FinancialLedger.ACCOUNT_PAYABLE_VENDOR,
            FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
            FinancialLedger.ACCOUNT_ACCRUED_LIABILITY,
            FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
            FinancialLedger.ACCOUNT_ZAKAT_PAYABLE,
            FinancialLedger.ACCOUNT_VAT_PAYABLE,
        ]
        
        total_assets = Decimal('0')
        asset_details = []
        for acc in assets:
            bal = FinancialLedger.objects.filter(farm=self.farm, account_code=acc).aggregate(
                net=Sum('debit') - Sum('credit')
            )['net'] or Decimal('0')
            total_assets += bal
            asset_details.append({'name': dict(FinancialLedger.ACCOUNT_CHOICES).get(acc, acc), 'balance': bal})
            
        total_liabilities = Decimal('0')
        liability_details = []
        for acc in liabilities:
            bal = FinancialLedger.objects.filter(farm=self.farm, account_code=acc).aggregate(
                net=Sum('credit') - Sum('debit')
            )['net'] or Decimal('0')
            total_liabilities += bal
            liability_details.append({'name': dict(FinancialLedger.ACCOUNT_CHOICES).get(acc, acc), 'balance': bal})
            
        return {
            'assets': asset_details,
            'total_assets': total_assets,
            'liabilities': liability_details,
            'total_liabilities': total_liabilities,
            'equity': total_assets - total_liabilities
        }
