"""
Agri-Guardian: Comprehensive Farm Extension (Al Mahmadieh)
Adds full agricultural ecosystem:
- Crops (محاصيل)
- Perennial Trees (أشجار معمرة)
- Wells & Machines (آبار وآلات)
- Daily Activities (أنشطة يومية)
- Crop Plans (خطط المحاصيل)
- Financial Integration (التكامل المالي)
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
from django.db.models import Sum
from smart_agri.core.models.farm import Farm, Location, Asset, LocationWell
from smart_agri.core.models.crop import Crop, CropVariety
from smart_agri.core.models.task import Task
from smart_agri.core.models.planning import Season, CropPlan
from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.tree import LocationTreeStock, TreeStockEvent, TreeProductivityStatus
from smart_agri.inventory.models import Item, Unit
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.sales.models import Customer, SalesInvoice, SalesInvoiceItem

def banner(text):
    print(f"\n{'='*60}\n{text}\n{'='*60}")

try:
    with transaction.atomic():
        banner("🌿 توسعة شاملة لمزرعة المحمدية")
        
        # Get existing farm
        farm = Farm.objects.filter(slug="al-mahmadieh-farm").first()
        if not farm:
            print("❌ Farm not found! Run populate_mahmadieh_farm.py first.")
            sys.exit(1)
        
        user = User.objects.filter(username="admin_mahmadieh").first()
        if not user:
            user = User.objects.first()
        
        print(f"  📍 Farm: {farm.name} (ID: {farm.id})")
        
        # ═══════════════════════════════════════════════════════════════
        # 1. CROPS & VARIETIES (المحاصيل والأصناف)
        # ═══════════════════════════════════════════════════════════════
        banner("🌾 المحاصيل والأصناف")
        
        # Wheat (annual crop)
        wheat, _ = Crop.objects.get_or_create(
            name="قمح",
            defaults={"mode": "Open", "is_perennial": False}
        )
        print(f"  ✅ Crop: {wheat.name} (Annual)")
        
        # Mango (perennial tree)
        mango, _ = Crop.objects.get_or_create(
            name="مانجو",
            defaults={"mode": "Open", "is_perennial": True}
        )
        print(f"  ✅ Crop: {mango.name} (Perennial)")
        
        # Date Palm (perennial tree)
        dates, _ = Crop.objects.get_or_create(
            name="نخيل",
            defaults={"mode": "Open", "is_perennial": True}
        )
        print(f"  ✅ Crop: {dates.name} (Perennial)")
        
        # Create Varieties
        varieties_data = [
            {"crop": mango, "name": "تيمور", "code": "MANGO-TIMOR", "days": 90},
            {"crop": mango, "name": "عويس", "code": "MANGO-OWAIS", "days": 85},
            {"crop": dates, "name": "سكري", "code": "DATE-SUKARI", "days": 180},
            {"crop": dates, "name": "خلاص", "code": "DATE-KHALAS", "days": 170},
            {"crop": wheat, "name": "قمح بلدي", "code": "WHEAT-LOCAL", "days": 120},
        ]
        
        varieties = {}
        for v in varieties_data:
            variety, _ = CropVariety.objects.get_or_create(
                crop=v["crop"],
                name=v["name"],
                defaults={
                    "code": v["code"],
                    "est_days_to_harvest": v["days"]
                }
            )
            varieties[v["code"]] = variety
            print(f"  ✅ Variety: {variety}")
        
        # ═══════════════════════════════════════════════════════════════
        # 2. WELLS & ASSETS (الآبار والأصول)
        # ═══════════════════════════════════════════════════════════════
        banner("🛠️ الآبار والآلات")
        
        # Create Assets
        assets_data = [
            {"name": "بئر المحمدية الرئيسي", "category": "Well", "code": "WELL-MHM-01", "value": 500000},
            {"name": "بئر الحقل الشمالي", "category": "Well", "code": "WELL-MHM-02", "value": 350000},
            {"name": "جرار نيوهولاند", "category": "Machinery", "code": "TRACTOR-01", "value": 800000},
            {"name": "حصادة قمح", "category": "Machinery", "code": "HARVESTER-01", "value": 1200000},
            {"name": "منظومة ري بالتنقيط", "category": "Irrigation", "code": "DRIP-01", "value": 150000},
        ]
        
        assets = {}
        for a in assets_data:
            # Use filter/first to avoid sequence issues
            asset = Asset.objects.filter(farm=farm, code=a["code"]).first()
            if not asset:
                try:
                    asset = Asset.objects.create(
                        farm=farm,
                        code=a["code"],
                        name=a["name"],
                        category=a["category"],
                        purchase_value=Decimal(str(a["value"]))
                    )
                except Exception as e:
                    print(f"  ⚠️ Asset {a['name']} already exists or error: {e}")
                    asset = Asset.objects.filter(farm=farm, name=a["name"]).first()
            
            if asset:
                assets[a["code"]] = asset
                print(f"  ✅ Asset: {asset.name} ({asset.category}) - {a['value']:,} ریال")
        
        # Link Wells to Locations
        locations = list(Location.objects.filter(farm=farm))
        warehouse = locations[0] if locations else None
        
        for loc in locations:
            if loc.code and "FLD" in loc.code:
                well_code = "WELL-MHM-01" if "01" in loc.code else "WELL-MHM-02"
                if well_code in assets:
                    well_link, created = LocationWell.objects.get_or_create(
                        location=loc,
                        asset=assets[well_code],
                        defaults={
                            "well_depth": Decimal("50"),
                            "pump_type": "غاطس كهربائي",
                            "capacity_lps": Decimal("15"),
                            "is_operational": True
                        }
                    )
                    if created:
                        print(f"  ✅ Well Link: {loc.name} → {assets[well_code].name}")
        
        # ═══════════════════════════════════════════════════════════════
        # 3. PERENNIAL TREES (الأشجار المعمرة)
        # ═══════════════════════════════════════════════════════════════
        banner("🌳 الأشجار المعمرة")
        
        # Create Productivity Status
        prod_status, _ = TreeProductivityStatus.objects.get_or_create(
            code="PRODUCTIVE",
            defaults={"name_en": "Productive", "name_ar": "منتجة"}
        )
        
        young_status, _ = TreeProductivityStatus.objects.get_or_create(
            code="YOUNG",
            defaults={"name_en": "Young/Non-bearing", "name_ar": "صغيرة/غير مثمرة"}
        )
        
        # Add trees to locations
        tree_data = [
            {"loc_code": "FLD-MHM-01", "variety": "MANGO-TIMOR", "count": 150, "status": prod_status},
            {"loc_code": "FLD-MHM-01", "variety": "MANGO-OWAIS", "count": 100, "status": young_status},
            {"loc_code": "FLD-MHM-02", "variety": "DATE-SUKARI", "count": 200, "status": prod_status},
            {"loc_code": "FLD-MHM-02", "variety": "DATE-KHALAS", "count": 80, "status": prod_status},
        ]
        
        for td in tree_data:
            location = Location.objects.filter(farm=farm, code=td["loc_code"]).first()
            variety = varieties.get(td["variety"])
            if location and variety:
                tree_stock, created = LocationTreeStock.objects.get_or_create(
                    location=location,
                    crop_variety=variety,
                    defaults={
                        "current_tree_count": td["count"],
                        "productivity_status": td["status"],
                        "planting_date": date(2020, 1, 1)
                    }
                )
                if not created:
                    tree_stock.current_tree_count = td["count"]
                    tree_stock.save()
                print(f"  ✅ Trees: {td['count']} {variety.name} @ {location.name}")
        
        # ═══════════════════════════════════════════════════════════════
        # 4. SEASON & CROP PLANS (الموسم وخطط المحاصيل)
        # ═══════════════════════════════════════════════════════════════
        banner("📅 الموسم وخطط المحاصيل")
        
        # Create Season
        season_2026, _ = Season.objects.get_or_create(
            name="موسم 2026",
            defaults={
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 12, 31),
                "is_active": True
            }
        )
        print(f"  ✅ Season: {season_2026.name}")
        
        # Create Crop Plans
        for loc in locations:
            if loc.code == "FLD-MHM-01":
                crop_plan, _ = CropPlan.objects.get_or_create(
                    farm=farm,
                    crop=mango,
                    location=loc,
                    season=season_2026,
                    defaults={
                        "name": f"خطة المانجو - {loc.name}",
                        "start_date": date(2026, 3, 1),
                        "end_date": date(2026, 9, 30),
                        "expected_yield": Decimal("5000"),
                        "yield_unit": "kg",
                        "budget_amount": Decimal("50000"),
                        "created_by": user
                    }
                )
                print(f"  ✅ Crop Plan: {crop_plan.name}")
                
            elif loc.code == "FLD-MHM-02":
                crop_plan, _ = CropPlan.objects.get_or_create(
                    farm=farm,
                    crop=dates,
                    location=loc,
                    season=season_2026,
                    defaults={
                        "name": f"خطة النخيل - {loc.name}",
                        "start_date": date(2026, 6, 1),
                        "end_date": date(2026, 10, 31),
                        "expected_yield": Decimal("8000"),
                        "yield_unit": "kg",
                        "budget_amount": Decimal("40000"),
                        "created_by": user
                    }
                )
                print(f"  ✅ Crop Plan: {crop_plan.name}")
        
        # ═══════════════════════════════════════════════════════════════
        # 5. TASKS (المهام الزراعية)
        # ═══════════════════════════════════════════════════════════════
        banner("📋 المهام الزراعية")
        
        tasks_data = [
            {"crop": mango, "stage": "إعداد", "name": "تقليم الأشجار", "asset_type": "TREE", "is_perennial": True},
            {"crop": mango, "stage": "رعاية", "name": "ري الأشجار", "asset_type": "TREE", "requires_well": True},
            {"crop": mango, "stage": "رعاية", "name": "تسميد الأشجار", "asset_type": "TREE", "is_perennial": True},
            {"crop": mango, "stage": "حصاد", "name": "جني المانجو", "asset_type": "TREE", "is_harvest": True},
            {"crop": dates, "stage": "رعاية", "name": "تنظيف النخيل", "asset_type": "TREE", "is_perennial": True},
            {"crop": dates, "stage": "حصاد", "name": "جني التمور", "asset_type": "TREE", "is_harvest": True},
            {"crop": wheat, "stage": "زراعة", "name": "بذر القمح", "asset_type": "SECTOR"},
            {"crop": wheat, "stage": "حصاد", "name": "حصاد القمح", "asset_type": "MACHINE", "requires_machinery": True},
        ]
        
        tasks = {}
        for t in tasks_data:
            task, _ = Task.objects.get_or_create(
                crop=t["crop"],
                stage=t["stage"],
                name=t["name"],
                defaults={
                    "target_asset_type": t.get("asset_type", "NONE"),
                    "is_perennial_procedure": t.get("is_perennial", False),
                    "is_harvest_task": t.get("is_harvest", False),
                    "requires_well": t.get("requires_well", False),
                    "requires_machinery": t.get("requires_machinery", False)
                }
            )
            tasks[t["name"]] = task
            print(f"  ✅ Task: {task.name} ({task.stage})")
        
        # ═══════════════════════════════════════════════════════════════
        # 6. DAILY LOG & ACTIVITIES (السجل اليومي والأنشطة)
        # ═══════════════════════════════════════════════════════════════
        banner("📝 السجل اليومي والأنشطة")
        
        # Create Daily Log for today
        from smart_agri.core.constants import DailyLogStatus
        daily_log, _ = DailyLog.objects.get_or_create(
            farm=farm,
            log_date=date.today(),
            defaults={
                "status": DailyLogStatus.SUBMITTED,
                "notes": "سجل يومي شامل للأنشطة الزراعية",
                "created_by": user
            }
        )
        print(f"  ✅ Daily Log: {daily_log.log_date} ({daily_log.status})")
        
        # Get crop plans
        mango_plan = CropPlan.objects.filter(farm=farm, crop=mango).first()
        
        # Create Activities
        activities_data = [
            {
                "task_name": "ري الأشجار",
                "location_code": "FLD-MHM-01",
                "hours": Decimal("4"),
                "team": "أحمد، خالد، محمد",
                "note": "ري أشجار المانجو - 250 شجرة"
            },
            {
                "task_name": "تسميد الأشجار",
                "location_code": "FLD-MHM-01",
                "hours": Decimal("3"),
                "team": "يحيى، عبدالله",
                "note": "تسميد المانجو بسماد NPK"
            },
            {
                "task_name": "تنظيف النخيل",
                "location_code": "FLD-MHM-02",
                "hours": Decimal("5"),
                "team": "محمد، يحيى",
                "note": "تنظيف وعناية بالنخيل - 280 شجرة"
            },
        ]
        
        for act_data in activities_data:
            task = tasks.get(act_data["task_name"])
            location = Location.objects.filter(farm=farm, code=act_data["location_code"]).first()
            
            if task and location:
                activity = Activity.objects.create(
                    log=daily_log,
                    task=task,
                    location=location,
                    crop=task.crop,
                    crop_plan=mango_plan if task.crop == mango else None,
                    hours=act_data["hours"],
                    team=act_data["team"],
                    created_by=user
                )
                print(f"  ✅ Activity: {task.name} @ {location.name} ({act_data['hours']}h)")
        
        # ═══════════════════════════════════════════════════════════════
        # 7. TREE HARVEST ACTIVITIES (أنشطة حصاد الأشجار)
        # ═══════════════════════════════════════════════════════════════
        banner("🌳🌾 أنشطة حصاد الأشجار")
        
        # Mango Harvest
        mango_harvest_task = tasks.get("جني المانجو")
        field_north = Location.objects.filter(farm=farm, code="FLD-MHM-01").first()
        
        if mango_harvest_task and field_north:
            # Create harvest activity
            harvest_activity = Activity.objects.create(
                log=daily_log,
                task=mango_harvest_task,
                location=field_north,
                crop=mango,
                crop_variety=varieties.get("MANGO-TIMOR"),
                hours=Decimal("6"),
                team="فريق الحصاد",
                activity_tree_count=50,
                created_by=user
            )
            print(f"  ✅ Mango Harvest: 50 trees harvested")
            
            # Create TreeStockEvent for harvest
            tree_stock = LocationTreeStock.objects.filter(
                location=field_north,
                crop_variety=varieties.get("MANGO-TIMOR")
            ).first()
            
            if tree_stock:
                TreeStockEvent.objects.create(
                    location_tree_stock=tree_stock,
                    activity=harvest_activity,
                    event_type=TreeStockEvent.HARVEST,
                    tree_count_delta=0,  # No tree count change for harvest
                    harvest_quantity=Decimal("500"),  # 500 kg
                    harvest_uom="kg",
                    notes="حصاد المانجو - 50 شجرة × 10 كجم"
                )
                print(f"  ✅ Harvest Event: 500 kg مانجو")
        
        # ═══════════════════════════════════════════════════════════════
        # 8. ADDITIONAL SALES INVOICES
        # ═══════════════════════════════════════════════════════════════
        banner("💰 فواتير مبيعات إضافية")
        
        # Create Mango Item if not exists
        unit_kg, _ = Unit.objects.get_or_create(code="kg", defaults={"name": "كيلوغرام"})
        
        mango_item, _ = Item.objects.get_or_create(
            name="مانجو تيمور",
            defaults={
                "group": "Products",
                "uom": "kg",
                "unit": unit_kg,
                "unit_price": Decimal("25.00")
            }
        )
        
        dates_item, _ = Item.objects.get_or_create(
            name="تمور سكري",
            defaults={
                "group": "Products",
                "uom": "kg",
                "unit": unit_kg,
                "unit_price": Decimal("35.00")
            }
        )
        
        # Add to inventory (harvest income)
        InventoryService.record_movement(
            farm=farm,
            item=mango_item,
            location=Location.objects.filter(farm=farm, code="WH-MHM-01").first(),
            qty_delta=Decimal("500"),
            ref_type="HARVEST",
            ref_id="HARVEST-MANGO-2026-001",
            note="حصاد المانجو تيمور",
            batch_number="MANGO-2026-001"
        )
        print(f"  ✅ Mango stock added: 500 kg")
        
        # Create sales invoice for mango
        customer = Customer.objects.filter(name="مخبز الأمانة").first()
        if customer:
            inv = SalesInvoice.objects.create(
                farm=farm,
                customer=customer,
                invoice_date=date.today(),
                status='approved',
                created_by=user,
                total_amount=Decimal("7500")
            )
            SalesInvoiceItem.objects.create(
                invoice=inv,
                item=mango_item,
                qty=Decimal("300"),
                unit_price=Decimal("25.00"),
                total=Decimal("7500")
            )
            InventoryService.record_movement(
                farm=farm,
                item=mango_item,
                location=Location.objects.filter(farm=farm, code="WH-MHM-01").first(),
                qty_delta=-Decimal("300"),
                ref_type="SALES",
                ref_id=str(inv.id),
                note=f"مبيعات مانجو - فاتورة #{inv.id}",
                batch_number="MANGO-2026-001"
            )
            print(f"  ✅ Invoice #{inv.id}: 300 kg مانجو @ 25 = 7,500 ریال")
        
        # ═══════════════════════════════════════════════════════════════
        # 9. FINAL SUMMARY
        # ═══════════════════════════════════════════════════════════════
        banner("📊 الملخص النهائي - التوسعة الشاملة")
        
        print("\n🌾 المحاصيل والأصناف:")
        print(f"   • محاصيل: {Crop.objects.count()}")
        print(f"   • أصناف: {CropVariety.objects.count()}")
        
        print("\n🛠️ الآبار والآلات:")
        print(f"   • أصول: {Asset.objects.filter(farm=farm).count()}")
        print(f"   • آبار مربوطة: {LocationWell.objects.filter(location__farm=farm).count()}")
        
        print("\n🌳 الأشجار المعمرة:")
        tree_total = LocationTreeStock.objects.filter(location__farm=farm).aggregate(total=Sum('current_tree_count'))
        print(f"   • إجمالي الأشجار: {tree_total['total'] or 0}")
        
        print("\n📅 خطط المحاصيل:")
        print(f"   • خطط نشطة: {CropPlan.objects.filter(farm=farm).count()}")
        
        print("\n📋 المهام:")
        print(f"   • مهام مسجلة: {Task.objects.count()}")
        
        print("\n📝 الأنشطة:")
        print(f"   • أنشطة اليوم: {Activity.objects.filter(log=daily_log).count()}")
        
        print("\n" + "="*60)
        print("🏆 تمت التوسعة الشاملة بنجاح!")
        print("="*60)

except Exception as e:
    import traceback
    print(f"\n❌ ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)
