
import os
import django
import sys
import uuid
from decimal import Decimal
from django.utils import timezone
from datetime import date

# 1. SETUP
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

# 2. IMPORTS
from django.contrib.auth.models import User
from smart_agri.core.models import Farm, Location, Crop
from smart_agri.core.models.hr import Employee
from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.activity import Activity
from smart_agri.finance.models import FinancialLedger, WorkerAdvance, ActualExpense
from smart_agri.inventory.services import InventoryService
from smart_agri.sales.services import SaleService
from smart_agri.inventory.models import Item
from smart_agri.sales.models import Customer, SalesInvoice

def log(msg):
    print(msg)
    try:
        with open('simulation.log', 'a', encoding='utf-8') as f:
            f.write(msg + '\n')
    except Exception:
        pass # Ignore file lock errors, print is sufficient

def simulate_cycle():
    log("\n" + "="*50)
    log("🚜 STARTING GOLDEN FARM FULL DOCUMENT CYCLE - ARABIC")
    log("="*50)
    
    # --- PHASE 1: CONTEXT ---
    try:
        sardud = Farm.objects.get(name='مزرعة سردود')
        loc_a = Location.objects.get(name="سردود - مربع أ")
        mgr = User.objects.get(username='manager_sardud')
        acct = User.objects.get(username='acct_sardud')
        tech = User.objects.get(username='tech_sardud')
        sup = User.objects.get(username='sup_sardud')
        cashier = User.objects.get(username='cash_sardud')
        log(f"✅ Context Loaded: Farm {sardud.name}, Team Loaded.")
    except Exception as e:
        log(f"❌ CRITICAL ERROR: Context missing. Have you run 'seed_golden_farm.py'?\nDetails: {e}")
        return

    # --- PHASE 2: ADMINISTRATIVE (HR / CASH ADVANCE) ---
    log("\n--- STEP 2: ADMINISTRATIVE (WORKER ADVANCE) ---")
    try:
        # Match employee by farm for safety
        worker = Employee.objects.filter(farm=sardud, first_name='علي').first()
        if not worker:
            worker = Employee.objects.filter(farm=sardud).first()

        if not worker:
            log("❌ No workers found! Seeding Error.")
            return

        advance = WorkerAdvance.objects.create(
            worker=worker,
            amount=Decimal('1000.0000'),
            supervisor=sup,
            notes="سلفة غداء (فريق سردود)",
            is_deducted=False
        )
        log(f"✅ Admin: Advance #{advance.id} issued to {worker.first_name} (1000 YER)")
    except Exception as e:
        log(f"❌ Admin Failed: {e}")

    # --- PHASE 3: TECHNICAL (DAILY LOG / ACTIVITY) ---
    log("\n--- STEP 3: TECHNICAL (DAILY LOG & ACTIVITY) ---")
    try:
        # Create Daily Log
        dlog, _ = DailyLog.objects.get_or_create(
            farm=sardud,
            log_date=date.today(),
            defaults={'supervisor': None, 'created_by': sup}
        )
        
        # Record Activity (Manual Labor)
        act = Activity.objects.create(
            log=dlog,
            location=loc_a,
            days_spent=Decimal('1.00'), # 1 Surra
            cost_total=Decimal('5000.0000'), # Estimation
            note="تقليم أشجار المانجو",
            created_by=sup,
            idempotency_key=uuid.uuid4()
        )
        log(f"✅ Technical: Daily Log #{dlog.id} - Activity #{act.id} Created (Pruning)")
    except Exception as e:
        log(f"❌ Technical Failed: {e}")
        import traceback
        traceback.print_exc()


    # --- PHASE 4: PROCUREMENT (DIESEL) ---
    log("\n--- STEP 4: PROCUREMENT (DIESEL) ---")
    try:
        diesel_item = Item.objects.get(name="ديزل")
        InventoryService.record_movement(
            farm=sardud,
            item=diesel_item,
            qty_delta=Decimal('5000'),
            location=loc_a,
            ref_type='OPENING',
            note='رصيد افتتاحي - ديزل',
            batch_number='BATCH-DSL-2026-001',
            actor_user=mgr
        )
        log("✅ Inventory: Injected 5000L Diesel")
    except Exception as e:
        log(f"❌ Procurement Failed: {e}")

    # --- PHASE 5: OPERATIONS (CONSUMPTION) ---
    log("\n--- STEP 5: OPERATIONS (IRRIGATION) ---")
    try:
        InventoryService.process_consumption(
            item_id=diesel_item.id,
            farm_id=sardud.id,
            quantity=Decimal('100'),
            user=tech,
            location_id=loc_a.id
        )
        log("✅ Operations: Consumed 100L Diesel")
    except Exception as e:
        log(f"❌ Operations Failed: {e}")

    # --- PHASE 6: SALES & FINANCE ---
    log("\n--- STEP 6: SALES (MANGO) ---")
    try:
        mango_fruit = Item.objects.get(name="ثمار مانجو")
        
        # Inject Harvest Stock first
        InventoryService.record_movement(
            farm=sardud,
            item=mango_fruit,
            qty_delta=Decimal('2000'),
            location=loc_a,
            ref_type='HARVEST',
            batch_number='BATCH-MNG-2026-001',
            actor_user=sup
        )

        cust, _ = Customer.objects.get_or_create(name="وكيل السوق المركزي", defaults={'customer_type': Customer.TYPE_WHOLESALER})
        
        inv_data = [{'item': mango_fruit, 'qty': 1000, 'unit_price': 1200}]
        
        invoice = SaleService.create_invoice(
            customer=cust,
            location=loc_a,
            invoice_date=date.today(),
            items_data=inv_data,
            user=mgr
        )
        
        if not invoice.idempotency_key:
            invoice.idempotency_key = uuid.uuid4()
            invoice.save()
        
        SaleService.confirm_sale(invoice, user=acct)
        log(f"✅ Sales: Invoice #{invoice.id} Confirmed (1000 KG Mango)")
        
        # Verify Ledger
        count = FinancialLedger.objects.filter(object_id=str(invoice.id)).count()
        if count >= 2:
            log(f"✅ Finance: {count} Ledger Entries Verified.")
        else:
            log("❌ Finance: Ledger Missing!")
            
    except Exception as e:
        log(f"❌ Sales Failed: {e}")

    log("\n✅ SIMULATION CYCLE COMPLETE.")

if __name__ == '__main__':
    simulate_cycle()
