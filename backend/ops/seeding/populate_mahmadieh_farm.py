"""
Agri-Guardian: Comprehensive Farm Data Population (Al Mahmadieh)
Creates complete initial data for مزرعة المحمدية covering all units:
- Administrative (Employees, Contracts)
- Technical (Locations, Items, Operations, Harvest)
- Financial (Customers, Invoices, Ledger)
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
from smart_agri.core.models.hr import Employee, EmploymentContract
from smart_agri.inventory.models import Item, Unit, StockMovement, ItemInventory
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.finance.models import FinancialLedger
from smart_agri.sales.models import Customer, SalesInvoice, SalesInvoiceItem

def banner(text):
    print(f"\n{'='*60}\n{text}\n{'='*60}")

try:
    with transaction.atomic():
        banner("🌾 مزرعة المحمدية - إعداد البيانات الشاملة")
        
        # ═══════════════════════════════════════════════════════════════
        # 1. FARM & USER SETUP
        # ═══════════════════════════════════════════════════════════════
        print("\n📋 Step 1: إنشاء المزرعة والمستخدم...")
        
        user = User.objects.filter(username="admin_mahmadieh").first()
        if not user:
            user = User.objects.create_user(
                'admin_mahmadieh', 
                'admin@mahmadieh.farm', 
                'mahmadieh2026'
            )
            user.first_name = "أحمد"
            user.last_name = "العامري"
            user.save()
            print(f"  ✅ Created user: {user.username}")
        
        farm, created = Farm.objects.get_or_create(
            slug="al-mahmadieh-farm",
            defaults={
                "name": "مزرعة المحمدية الزراعية",
                "region": "المحمدية - صنعاء"
            }
        )
        print(f"  ✅ Farm: {farm.name} (ID: {farm.id})")

        # ═══════════════════════════════════════════════════════════════
        # 2. ADMINISTRATIVE UNIT (الوحدة الإدارية)
        # ═══════════════════════════════════════════════════════════════
        banner("👥 الوحدة الإدارية - الموظفين والعقود")
        
        employees_data = [
            {"first_name": "أحمد", "last_name": "محمد العامري", "employee_id": "EMP-MHM-001", 
             "role": "Manager", "id_number": "12345678", "basic": 150000, "housing": 30000, "transport": 10000},
            {"first_name": "خالد", "last_name": "علي السعيدي", "employee_id": "EMP-MHM-002", 
             "role": "Engineer", "id_number": "12345679", "basic": 100000, "housing": 20000, "transport": 8000},
            {"first_name": "محمد", "last_name": "سعيد الحميدي", "employee_id": "EMP-MHM-003", 
             "role": "Worker", "id_number": "12345680", "basic": 75000, "housing": 15000, "transport": 5000},
            {"first_name": "يحيى", "last_name": "أحمد القاضي", "employee_id": "EMP-MHM-004", 
             "role": "Worker", "id_number": "12345681", "basic": 50000, "housing": 10000, "transport": 5000},
            {"first_name": "عبدالله", "last_name": "محمد ناصر", "employee_id": "EMP-MHM-005", 
             "role": "Worker", "id_number": "12345682", "basic": 40000, "housing": 8000, "transport": 4000},
        ]
        
        created_employees = []
        for emp_data in employees_data:
            emp, created = Employee.objects.get_or_create(
                employee_id=emp_data["employee_id"],
                defaults={
                    "farm": farm,
                    "first_name": emp_data["first_name"],
                    "last_name": emp_data["last_name"],
                    "id_number": emp_data["id_number"],
                    "role": emp_data["role"],
                    "joined_date": date(2026, 1, 1),
                    "is_active": True
                }
            )
            created_employees.append(emp)
            
            # Create contract
            contract, _ = EmploymentContract.objects.get_or_create(
                employee=emp,
                start_date=date(2026, 1, 1),
                defaults={
                    "basic_salary": Decimal(str(emp_data["basic"])),
                    "housing_allowance": Decimal(str(emp_data["housing"])),
                    "transport_allowance": Decimal(str(emp_data["transport"])),
                    "other_allowance": Decimal("0"),
                    "is_active": True
                }
            )
            
            total_pkg = contract.total_monthly_package()
            print(f"  ✅ {emp.first_name} {emp.last_name} ({emp.role}) - {total_pkg:,.0f} ریال/شهر")
        
        total_payroll = sum(c.total_monthly_package() for e in created_employees for c in e.contracts.filter(is_active=True))
        print(f"\n  📊 إجمالي الرواتب الشهرية: {total_payroll:,.0f} ریال")

        # ═══════════════════════════════════════════════════════════════
        # 3. TECHNICAL UNIT - LOCATIONS
        # ═══════════════════════════════════════════════════════════════
        banner("📍 الوحدة الفنية - المواقع")
        
        warehouse, _ = Location.objects.get_or_create(
            farm=farm, code="WH-MHM-01",
            defaults={"name": "المستودع الرئيسي", "type": "warehouse"}
        )
        print(f"  ✅ {warehouse.name} ({warehouse.code})")
        
        field_north, _ = Location.objects.get_or_create(
            farm=farm, code="FLD-MHM-01",
            defaults={"name": "الحقل الشمالي", "type": "Field"}
        )
        print(f"  ✅ {field_north.name} ({field_north.code})")
        
        field_south, _ = Location.objects.get_or_create(
            farm=farm, code="FLD-MHM-02",
            defaults={"name": "الحقل الجنوبي", "type": "Field"}
        )
        print(f"  ✅ {field_south.name} ({field_south.code})")

        # ═══════════════════════════════════════════════════════════════
        # 4. TECHNICAL UNIT - INVENTORY ITEMS
        # ═══════════════════════════════════════════════════════════════
        banner("📦 الوحدة الفنية - المخزون")
        
        unit_kg, _ = Unit.objects.get_or_create(code="kg", defaults={"name": "كيلوغرام"})
        unit_l, _ = Unit.objects.get_or_create(code="L", defaults={"name": "لتر"})
        
        items_data = [
            {"name": "بذور القمح", "group": "Materials", "uom": "kg", "unit": unit_kg, "price": Decimal("8.50")},
            {"name": "سماد يوريا", "group": "Materials", "uom": "kg", "unit": unit_kg, "price": Decimal("12.00")},
            {"name": "مبيد حشري", "group": "Materials", "uom": "L", "unit": unit_l, "price": Decimal("45.00")},
            {"name": "سولار", "group": "Fuel", "uom": "L", "unit": unit_l, "price": Decimal("350.00")},
            {"name": "قمح محصود", "group": "Products", "uom": "kg", "unit": unit_kg, "price": Decimal("15.00")},
        ]
        
        items = {}
        for item_data in items_data:
            item, _ = Item.objects.get_or_create(
                name=item_data["name"],
                defaults={
                    "group": item_data["group"],
                    "uom": item_data["uom"],
                    "unit": item_data["unit"],
                    "unit_price": item_data["price"]
                }
            )
            items[item_data["name"]] = item
            print(f"  ✅ {item.name} ({item.group}) @ {item.unit_price} ریال/{item.uom}")

        # ═══════════════════════════════════════════════════════════════
        # 5. TECHNICAL UNIT - GRN (PURCHASES)
        # ═══════════════════════════════════════════════════════════════
        banner("🛒 الوحدة الفنية - المشتريات (GRN)")
        
        purchases = [
            {"item": "بذور القمح", "qty": 500, "cost": Decimal("8.50"), "ref": "PO-MHM-001", "batch": "SEEDS-MHM-2026"},
            {"item": "سماد يوريا", "qty": 200, "cost": Decimal("12.00"), "ref": "PO-MHM-002", "batch": "FERT-MHM-2026"},
            {"item": "مبيد حشري", "qty": 50, "cost": Decimal("45.00"), "ref": "PO-MHM-003", "batch": "PEST-MHM-2026"},
            {"item": "سولار", "qty": 100, "cost": Decimal("350.00"), "ref": "PO-MHM-004", "batch": "FUEL-MHM-2026"},
        ]
        
        total_purchases = Decimal("0")
        for p in purchases:
            item = items[p["item"]]
            InventoryService.process_grn(
                farm=farm,
                item=item,
                location=warehouse,
                qty=Decimal(str(p["qty"])),
                unit_cost=p["cost"],
                ref_id=p["ref"],
                batch_number=p["batch"]
            )
            line_total = Decimal(str(p["qty"])) * p["cost"]
            total_purchases += line_total
            print(f"  ✅ {p['qty']} {item.uom} {item.name} @ {p['cost']} = {line_total:,.0f} ریال")
        
        print(f"\n  📊 إجمالي المشتريات: {total_purchases:,.0f} ریال")

        # ═══════════════════════════════════════════════════════════════
        # 6. TECHNICAL UNIT - OPERATIONS
        # ═══════════════════════════════════════════════════════════════
        banner("⚙️ الوحدة الفنية - العمليات الزراعية")
        
        operations = [
            {"item": "بذور القمح", "qty": -100, "type": "ACTIVITY_SOWING", "ref": "ACT-MHM-SOWING-001", 
             "note": "زراعة القمح - الحقل الشمالي", "batch": "SEEDS-MHM-2026"},
            {"item": "سماد يوريا", "qty": -50, "type": "ACTIVITY_FERTILIZATION", "ref": "ACT-MHM-FERT-001", 
             "note": "تسميد القمح - المرحلة الأولى", "batch": "FERT-MHM-2026"},
            {"item": "مبيد حشري", "qty": -15, "type": "ACTIVITY_PEST_CONTROL", "ref": "ACT-MHM-PEST-001", 
             "note": "رش مبيد حشري - مكافحة الآفات", "batch": "PEST-MHM-2026"},
            {"item": "سولار", "qty": -40, "type": "MACHINE_USAGE", "ref": "ACT-MHM-FUEL-001", 
             "note": "تشغيل الجرار الزراعي", "batch": "FUEL-MHM-2026"},
        ]
        
        for op in operations:
            item = items[op["item"]]
            InventoryService.record_movement(
                farm=farm,
                item=item,
                location=warehouse,
                qty_delta=Decimal(str(op["qty"])),
                ref_type=op["type"],
                ref_id=op["ref"],
                note=op["note"],
                batch_number=op["batch"]
            )
            print(f"  ✅ {op['type']}: استهلاك {abs(op['qty'])} {item.uom} {item.name}")

        # ═══════════════════════════════════════════════════════════════
        # 7. TECHNICAL UNIT - HARVEST
        # ═══════════════════════════════════════════════════════════════
        banner("🌾 الوحدة الفنية - الحصاد")
        
        harvest_qty = Decimal("2000")
        InventoryService.record_movement(
            farm=farm,
            item=items["قمح محصود"],
            location=warehouse,
            qty_delta=harvest_qty,
            ref_type="HARVEST",
            ref_id="HARVEST-MHM-2026-001",
            note="محصول القمح - الحقل الشمالي",
            batch_number="CROP-MHM-2026-001"
        )
        print(f"  ✅ حصاد: {harvest_qty} kg قمح محصود")

        # ═══════════════════════════════════════════════════════════════
        # 8. FINANCIAL UNIT - CUSTOMERS
        # ═══════════════════════════════════════════════════════════════
        banner("💰 الوحدة المالية - العملاء")
        
        customers_data = [
            {"name": "مخبز الأمانة", "type": "wholesaler", "phone": "777-111-222"},
            {"name": "تاجر الحبوب المركزي", "type": "wholesaler", "phone": "777-333-444"},
            {"name": "مطحنة السعادة", "type": "wholesaler", "phone": "777-555-666"},
        ]
        
        customers = {}
        for c in customers_data:
            customer, _ = Customer.objects.get_or_create(
                name=c["name"],
                defaults={"customer_type": c["type"], "phone": c["phone"]}
            )
            customers[c["name"]] = customer
            print(f"  ✅ {customer.name} ({customer.customer_type})")

        # ═══════════════════════════════════════════════════════════════
        # 9. FINANCIAL UNIT - SALES INVOICES
        # ═══════════════════════════════════════════════════════════════
        banner("📄 الوحدة المالية - فواتير المبيعات")
        
        invoices_data = [
            {"customer": "مخبز الأمانة", "qty": 500, "price": Decimal("15.00")},
            {"customer": "تاجر الحبوب المركزي", "qty": 300, "price": Decimal("14.50")},
            {"customer": "مطحنة السعادة", "qty": 400, "price": Decimal("15.00")},
        ]
        
        total_sales = Decimal("0")
        for inv_data in invoices_data:
            customer = customers[inv_data["customer"]]
            qty = Decimal(str(inv_data["qty"]))
            price = inv_data["price"]
            total = qty * price
            
            # Create Invoice
            invoice = SalesInvoice.objects.create(
                farm=farm,
                customer=customer,
                invoice_date=date.today(),
                status='draft',
                created_by=user,
                total_amount=Decimal("0")
            )
            
            # Add Line Item
            SalesInvoiceItem.objects.create(
                invoice=invoice,
                item=items["قمح محصود"],
                qty=qty,
                unit_price=price,
                total=total
            )
            
            # Deduct from stock
            InventoryService.record_movement(
                farm=farm,
                item=items["قمح محصود"],
                location=warehouse,
                qty_delta=-qty,
                ref_type="SALES",
                ref_id=str(invoice.id),
                note=f"فاتورة مبيعات #{invoice.id} - {customer.name}",
                batch_number="CROP-MHM-2026-001"
            )
            
            # Approve Invoice
            invoice.status = 'approved'
            invoice.total_amount = total
            invoice.save()
            
            total_sales += total
            print(f"  ✅ Invoice #{invoice.id}: {customer.name} - {qty} kg @ {price} = {total:,.0f} ریال")
        
        print(f"\n  📊 إجمالي المبيعات: {total_sales:,.0f} ریال")

        # ═══════════════════════════════════════════════════════════════
        # 10. FINAL SUMMARY
        # ═══════════════════════════════════════════════════════════════
        banner("📊 الملخص النهائي - مزرعة المحمدية")
        
        print("\n🔸 الوحدة الإدارية:")
        print(f"   • عدد الموظفين: {len(created_employees)}")
        print(f"   • إجمالي الرواتب الشهرية: {total_payroll:,.0f} ریال")
        
        print("\n🔸 الوحدة الفنية:")
        seeds_stock = InventoryService.get_stock_level(farm, items["بذور القمح"], warehouse)
        fert_stock = InventoryService.get_stock_level(farm, items["سماد يوريا"], warehouse)
        pest_stock = InventoryService.get_stock_level(farm, items["مبيد حشري"], warehouse)
        fuel_stock = InventoryService.get_stock_level(farm, items["سولار"], warehouse)
        wheat_stock = InventoryService.get_stock_level(farm, items["قمح محصود"], warehouse)
        
        print(f"   • بذور القمح: {seeds_stock:,.0f} kg (مشتريات: 500, مستهلك: 100)")
        print(f"   • سماد يوريا: {fert_stock:,.0f} kg (مشتريات: 200, مستهلك: 50)")
        print(f"   • مبيد حشري: {pest_stock:,.0f} L (مشتريات: 50, مستهلك: 15)")
        print(f"   • سولار: {fuel_stock:,.0f} L (مشتريات: 100, مستهلك: 40)")
        print(f"   • قمح محصود: {wheat_stock:,.0f} kg (حصاد: 2000, مباع: 1200)")
        
        print("\n🔸 الوحدة المالية:")
        print(f"   • عدد الفواتير: {len(invoices_data)}")
        print(f"   • إجمالي المبيعات: {total_sales:,.0f} ریال")
        print(f"   • إجمالي المشتريات: {total_purchases:,.0f} ریال")
        print(f"   • صافي الربح (تقريبي): {total_sales - total_purchases:,.0f} ریال")
        
        print("\n" + "="*60)
        print("🏆 تم إعداد بيانات مزرعة المحمدية بنجاح!")
        print("="*60)

except Exception as e:
    import traceback
    print(f"\n❌ ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
