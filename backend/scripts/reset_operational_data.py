import os
import sys
import django

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from django.db import transaction
from django.db.models import F

from smart_agri.core.models.log import DailyLog, MaterialVarianceAlert
from smart_agri.core.models.activity import Activity, ActivityItem
from smart_agri.core.models.inventory import ItemInventory, StockMovement, TreeCensusVarianceAlert, HarvestLot
from smart_agri.core.models.planning import CropPlan, CropPlanBudgetLine
from smart_agri.finance.models import ActualExpense, FinancialLedger, ApprovalRequest, FiscalPeriod
from smart_agri.finance.models_treasury import TreasuryTransaction
from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem

from django.db import transaction, connection

def bypass_delete(model):
    table = model._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(f"ALTER TABLE {table} DISABLE TRIGGER ALL;")
        cursor.execute(f"DELETE FROM {table};")
        cursor.execute(f"ALTER TABLE {table} ENABLE TRIGGER ALL;")

def reset_operational_data():
    print("⚠️ WARNING: This script will DELETE all operational data (Logs, Ledgers, Invoices, Inventory balances).")
    print("Master data (Crops, Farms, Users, Items, Plans) will be PRESERVED.")
    
    with transaction.atomic():
        print("1. Deleting Financial Data...")
        bypass_delete(ActualExpense)
        bypass_delete(FinancialLedger)
        bypass_delete(TreasuryTransaction)
        bypass_delete(ApprovalRequest)
        
        print("2. Deleting Sales Data...")
        bypass_delete(SalesInvoiceItem)
        bypass_delete(SalesInvoice)
        
        print("3. Deleting Harvest Data...")
        bypass_delete(HarvestLot)

        print("4. Deleting Daily Logs and Activities...")
        bypass_delete(ActivityItem)
        bypass_delete(Activity)
        bypass_delete(DailyLog)
        
        print("5. Deleting Alerts...")
        bypass_delete(MaterialVarianceAlert)
        bypass_delete(TreeCensusVarianceAlert)
        
        print("6. Resetting Inventory...")
        bypass_delete(StockMovement)
        bypass_delete(ItemInventory)
        
        print("7. Ensuring at least one OPEN Fiscal Period...")
        period = FiscalPeriod.objects.filter(status=FiscalPeriod.STATUS_OPEN).first()
        if not period:
            print("  ❌ No open fiscal period found! Creating one...")
            # Ideally, we should ensure the seed data has this. 
            print("  Please make sure to configure a Fiscal Year and Period in the admin panel.")
        else:
            print(f"  ✅ Open Fiscal Period found: {period.month}/{period.fiscal_year.year} ({period.fiscal_year.farm.name})")

        print("8. Checking active Crop Plans...")
        plans = CropPlan.objects.filter(status='active', deleted_at__isnull=True)
        if not plans.exists():
             print("  ⚠️ No active Crop Plans found. Simple mode requires an active plan.")
        else:
             print(f"  ✅ Found {plans.count()} active Crop Plans.")
             
        print("9. Checking Seeded Items...")
        from smart_agri.core.models.inventory import Item
        items = Item.objects.filter(deleted_at__isnull=True)
        print(f"  ✅ Found {items.count()} Items in master data.")
        
        print("🎉 Operational data successfully wiped. System is ready for the documentary cycle test.")

if __name__ == '__main__':
    reset_operational_data()
