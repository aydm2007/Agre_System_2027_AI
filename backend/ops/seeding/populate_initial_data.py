"""
Agri-Guardian: Initial Data Population Script (End User Perspective)
Creates realistic sample data for testing and demonstration purposes.
"""
import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from smart_agri.core.models.farm import Farm, Location
from smart_agri.inventory.models import Item, Unit, StockMovement, ItemInventory
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.finance.models import FinancialLedger
from smart_agri.sales.models import Customer, SalesInvoice, SalesInvoiceItem

print("=" * 60)
print("🌾 Agri-Guardian: Initial Data Population")
print("=" * 60)

try:
    with transaction.atomic():
        # ─────────────────────────────────────────────────────────────────
        # 1. CLEAR OLD TEST DATA (Fresh Start)
        # ─────────────────────────────────────────────────────────────────
        print("\n📋 Step 1: Clearing previous test data...")
        
        # Get test user and farm
        user = User.objects.filter(username="ibrahim").first()
        if not user:
            user = User.objects.create_user('ibrahim', 'ibrahim@test.com', 'test123')
            print("  Created user: ibrahim")
        
        farm = Farm.objects.filter(slug="ibrahim-test-orchard").first()
        if not farm:
            farm = Farm.objects.create(
                name="Ibrahim Test Orchard",
                slug="ibrahim-test-orchard",
                address="Yemen, Sana'a",
                created_at=timezone.now(),
                updated_at=timezone.now()
            )
            print(f"  Created farm: {farm.name}")

        # Clear existing movements and invoices for this farm
        SalesInvoiceItem.objects.filter(invoice__farm=farm).delete()
        SalesInvoice.objects.filter(farm=farm).delete()
        StockMovement.objects.filter(farm=farm).delete()
        ItemInventory.objects.filter(farm=farm).delete()  # Reset inventory
        print("  ✅ Cleared old test data")

        # ─────────────────────────────────────────────────────────────────
        # 2. CREATE LOCATIONS
        # ─────────────────────────────────────────────────────────────────
        print("\n📍 Step 2: Setting up locations...")
        
        main_warehouse, _ = Location.objects.get_or_create(
            farm=farm, code="WH-MAIN",
            defaults={"name": "المستودع الرئيسي", "type": "warehouse"}
        )
        print(f"  Location: {main_warehouse.name}")
        
        field_north, _ = Location.objects.get_or_create(
            farm=farm, code="FIELD-N01",
            defaults={"name": "الحقل الشمالي", "type": "Field"}
        )
        print(f"  Location: {field_north.name}")

        # ─────────────────────────────────────────────────────────────────
        # 3. CREATE INVENTORY ITEMS (Seeds, Fertilizers, Harvest)
        # ─────────────────────────────────────────────────────────────────
        print("\n📦 Step 3: Creating inventory items...")
        
        unit_kg, _ = Unit.objects.get_or_create(code="kg", defaults={"name": "كيلوغرام"})
        unit_liter, _ = Unit.objects.get_or_create(code="L", defaults={"name": "لتر"})
        unit_bag, _ = Unit.objects.get_or_create(code="bag", defaults={"name": "كيس"})

        # Seeds
        wheat_seeds, _ = Item.objects.get_or_create(
            name="بذور القمح",
            defaults={"group": "Materials", "uom": "kg", "unit": unit_kg, "unit_price": Decimal("8.50")}
        )
        print(f"  Item: {wheat_seeds.name}")

        # Fertilizers
        urea_fertilizer, _ = Item.objects.get_or_create(
            name="سماد يوريا",
            defaults={"group": "Materials", "uom": "kg", "unit": unit_kg, "unit_price": Decimal("12.00")}
        )
        print(f"  Item: {urea_fertilizer.name}")

        # Products (Harvest)
        wheat_grain, _ = Item.objects.get_or_create(
            name="قمح محصود",
            defaults={"group": "Products", "uom": "kg", "unit": unit_kg, "unit_price": Decimal("15.00")}
        )
        print(f"  Item: {wheat_grain.name}")

        # ─────────────────────────────────────────────────────────────────
        # 4. RECORD PURCHASE (GRN) - As End User
        # ─────────────────────────────────────────────────────────────────
        print("\n🛒 Step 4: Recording purchases (GRN)...")
        
        # Purchase 1: Wheat Seeds
        InventoryService.process_grn(
            farm=farm,
            item=wheat_seeds,
            location=main_warehouse,
            qty=Decimal("200.00"),
            unit_cost=Decimal("8.50"),
            ref_id="PO-2026-001",
            batch_number="SEEDS-2026-A"
        )
        print(f"  ✅ GRN: 200 kg بذور القمح @ 8.50 = 1,700 ریال")

        # Purchase 2: Fertilizer
        InventoryService.process_grn(
            farm=farm,
            item=urea_fertilizer,
            location=main_warehouse,
            qty=Decimal("50.00"),
            unit_cost=Decimal("12.00"),
            ref_id="PO-2026-002",
            batch_number="FERT-2026-A"
        )
        print(f"  ✅ GRN: 50 kg سماد يوريا @ 12.00 = 600 ریال")

        # ─────────────────────────────────────────────────────────────────
        # 5. RECORD OPERATIONS (Consumption) - As End User
        # ─────────────────────────────────────────────────────────────────
        print("\n⚙️ Step 5: Recording operations (consumption)...")
        
        # Operation 1: Sowing - Use Seeds
        InventoryService.record_movement(
            farm=farm,
            item=wheat_seeds,
            location=main_warehouse,
            qty_delta=-Decimal("50.00"),
            ref_type="ACTIVITY_SOWING",
            ref_id="ACT-SOWING-001",
            note="زراعة القمح - الحقل الشمالي",
            batch_number="SEEDS-2026-A"
        )
        print(f"  ✅ Activity: استهلاك 50 kg بذور للزراعة")

        # Operation 2: Fertilization - Use Fertilizer
        InventoryService.record_movement(
            farm=farm,
            item=urea_fertilizer,
            location=main_warehouse,
            qty_delta=-Decimal("20.00"),
            ref_type="ACTIVITY_FERTILIZATION",
            ref_id="ACT-FERT-001",
            note="تسميد القمح - الحقل الشمالي",
            batch_number="FERT-2026-A"
        )
        print(f"  ✅ Activity: استهلاك 20 kg سماد للتسميد")

        # ─────────────────────────────────────────────────────────────────
        # 6. RECORD HARVEST (Production) - As End User
        # ─────────────────────────────────────────────────────────────────
        print("\n🌾 Step 6: Recording harvest (production)...")
        
        InventoryService.record_movement(
            farm=farm,
            item=wheat_grain,
            location=main_warehouse,
            qty_delta=Decimal("800.00"),
            ref_type="HARVEST",
            ref_id="HARVEST-2026-001",
            note="محصول القمح - الحقل الشمالي",
            batch_number="CROP-2026-001"
        )
        print(f"  ✅ Harvest: 800 kg قمح محصود تم إضافته للمخزون")

        # ─────────────────────────────────────────────────────────────────
        # 7. CREATE SALES INVOICES - As End User
        # ─────────────────────────────────────────────────────────────────
        print("\n💰 Step 7: Creating sales invoices...")
        
        # Customer 1
        customer1, _ = Customer.objects.get_or_create(
            name="مخبز النور",
            defaults={"phone": "777-123-456", "customer_type": "wholesaler"}
        )
        
        # Customer 2
        customer2, _ = Customer.objects.get_or_create(
            name="تاجر الحبوب",
            defaults={"phone": "777-654-321", "customer_type": "retailer"}
        )

        # Invoice 1: Sell 200kg wheat
        inv1 = SalesInvoice.objects.create(
            farm=farm,
            customer=customer1,
            invoice_date=date.today(),
            status='draft',
            created_by=user,
            total_amount=Decimal("0")
        )
        item1 = SalesInvoiceItem.objects.create(
            invoice=inv1,
            item=wheat_grain,
            qty=Decimal("200.00"),
            unit_price=Decimal("15.00"),
            total=Decimal("3000.00")
        )
        
        # Record stock deduction
        InventoryService.record_movement(
            farm=farm,
            item=wheat_grain,
            location=main_warehouse,
            qty_delta=-Decimal("200.00"),
            ref_type="SALES",
            ref_id=str(inv1.id),
            note=f"فاتورة مبيعات #{inv1.id}",
            batch_number="CROP-2026-001"
        )
        
        inv1.status = 'approved'
        inv1.total_amount = item1.total
        inv1.save()
        print(f"  ✅ Invoice #{inv1.id}: {customer1.name} - 200 kg @ 15.00 = 3,000 ریال")

        # Invoice 2: Sell 150kg wheat
        inv2 = SalesInvoice.objects.create(
            farm=farm,
            customer=customer2,
            invoice_date=date.today(),
            status='draft',
            created_by=user,
            total_amount=Decimal("0")
        )
        item2 = SalesInvoiceItem.objects.create(
            invoice=inv2,
            item=wheat_grain,
            qty=Decimal("150.00"),
            unit_price=Decimal("14.50"),
            total=Decimal("2175.00")
        )
        
        InventoryService.record_movement(
            farm=farm,
            item=wheat_grain,
            location=main_warehouse,
            qty_delta=-Decimal("150.00"),
            ref_type="SALES",
            ref_id=str(inv2.id),
            note=f"فاتورة مبيعات #{inv2.id}",
            batch_number="CROP-2026-001"
        )
        
        inv2.status = 'approved'
        inv2.total_amount = item2.total
        inv2.save()
        print(f"  ✅ Invoice #{inv2.id}: {customer2.name} - 150 kg @ 14.50 = 2,175 ریال")

        # ─────────────────────────────────────────────────────────────────
        # 8. FINAL SUMMARY
        # ─────────────────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("📊 FINAL INVENTORY SUMMARY")
        print("=" * 60)
        
        seeds_stock = InventoryService.get_stock_level(farm, wheat_seeds, main_warehouse)
        fert_stock = InventoryService.get_stock_level(farm, urea_fertilizer, main_warehouse)
        wheat_stock = InventoryService.get_stock_level(farm, wheat_grain, main_warehouse)
        
        print(f"  بذور القمح:   {seeds_stock:>10} kg (Purchased: 200, Used: 50)")
        print(f"  سماد يوريا:   {fert_stock:>10} kg (Purchased: 50, Used: 20)")
        print(f"  قمح محصود:   {wheat_stock:>10} kg (Harvested: 800, Sold: 350)")
        
        print("\n💵 SALES SUMMARY")
        print("-" * 40)
        total_sales = inv1.total_amount + inv2.total_amount
        print(f"  Total Invoices: 2")
        print(f"  Total Sales:    {total_sales:>10} ریال")
        
        print("\n🏆 Initial data populated successfully!")

except Exception as e:
    import traceback
    print(f"\n❌ ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
