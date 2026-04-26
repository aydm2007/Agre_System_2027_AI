import os
import django
import sys
import uuid
from decimal import Decimal
from datetime import date, timedelta

# Setup Django
sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import Farm, Location, Crop, CropVariety, FarmCrop, CropPlan, DailyLog, Activity, Task, FinancialLedger, CropPlanLocation, Supervisor
from smart_agri.inventory.models import Item
from smart_agri.core.models.inventory import BiologicalAssetCohort, BiologicalAssetTransaction
from smart_agri.core.models.tree import LocationTreeStock
from django.contrib.auth import get_user_model

User = get_user_model()

def seed_shabwah():
    print("🚀 Starting Operation Sovereign Finality: Shabwah Genesis...")
    
    # 1. Admin & Farm
    admin = User.objects.filter(username='admin').first()
    farm, created = Farm.objects.get_or_create(
        name='مزرعة شبوة',
        defaults={
            'code': 'SHB-01',
            'tier': 'LARGE',
            'area_ha': 300,
            'is_active': True
        }
    )
    if created: print(f"✅ Farm: {farm.name} (Created)")
    else: print(f"✅ Farm: {farm.name} (Exists)")

    # 1b. Grant Admin Membership (RLS Bypass)
    from smart_agri.accounts.models import FarmMembership
    FarmMembership.objects.get_or_create(
        user=admin,
        farm=farm,
        defaults={'role': 'مدير النظام'}
    )
    print("✅ Admin membership granted for Shabwah Farm (RLS Scope: ACTIVE).")

    # 2. Locations
    locations_data = [
        ('قطاع الذرة الشامل', 'FIELD', 50),
        ('مشروع الموز', 'FIELD', 40),
        ('حديقة المانجو', 'FIELD', 60),
        ('المستودع المركزي', 'WAREHOUSE', 0),
    ]
    locs = {}
    for name, ltype, area in locations_data:
        loc, _ = Location.objects.get_or_create(
            farm=farm,
            name=name,
            defaults={'type': ltype}
        )
        locs[name] = loc
    print("✅ Locations established.")

    # 3. Crops & Varieties
    crops_data = [
        ('ذرة شامي', 'Maize', False),
        ('مانجو تيمور', 'Mango', True),
        ('موز بلدي', 'Banana', True),
    ]
    for name, cname, perennial in crops_data:
        crop, _ = Crop.objects.get_or_create(
            name=name,
            defaults={'is_perennial': perennial, 'mode': 'Open'}
        )
        FarmCrop.objects.get_or_create(farm=farm, crop=crop)
        
        variety, _ = CropVariety.objects.get_or_create(
            crop=crop,
            name='صنف شبوة الأصيل',
            defaults={'code': f'SHB-{name[:2].upper()}'}
        )
    print("✅ Crops and Varieties defined.")

    # 4. Biological Cohorts & Stock Fix
    mango_crop = Crop.objects.get(name='مانجو تيمور')
    mango_variety = CropVariety.objects.get(crop=mango_crop)
    mango_loc = locs['حديقة المانجو']
    
    cohort, _ = BiologicalAssetCohort.objects.get_or_create(
        farm=farm,
        location=mango_loc,
        variety=mango_variety,
        crop=mango_crop,
        defaults={
            'status': 'PRODUCTIVE',
            'batch_name': 'بذور شبوة - دفعة 1',
            'quantity': 500,
            'planted_date': date(2022, 1, 1)
        }
    )
    
    # [FIX] Manually initialize stock node to prevent ERR_NEGATIVE_TREE_STOCK
    stock, _ = LocationTreeStock.objects.get_or_create(
        location=mango_loc,
        crop_variety=mango_variety,
        defaults={'current_tree_count': 500}
    )
    if stock.current_tree_count < 500:
        stock.current_tree_count = 500
        stock.save()

    print("✅ Biological Cohorts initialized.")

    # 5. Crop Plan
    plan, _ = CropPlan.objects.get_or_create(
        farm=farm,
        crop=mango_crop,
        name='خطة المانجو الموسمية - شبوة',
        defaults={
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 12, 31),
            'status': 'Active'
        }
    )
    # Link plan to location
    CropPlanLocation.objects.get_or_create(
        crop_plan=plan,
        location=mango_loc,
        defaults={'assigned_area': 60}
    )
    print("✅ Crop Plans activated and linked to locations.")

    # 6. Daily Log & Activities
    task_irrigation, _ = Task.objects.get_or_create(
        name='الري بالتنقيط',
        crop=mango_crop,
        defaults={'archetype': 'IRRIGATION', 'stage': 'Execution'}
    )
    
    supervisor, _ = Supervisor.objects.get_or_create(
        farm=farm,
        code='SUP-001',
        defaults={'name': 'مشرف شبوة الرئيسي'}
    )
    
    log, _ = DailyLog.objects.get_or_create(
        farm=farm,
        log_date=date.today(),
        defaults={'supervisor': supervisor, 'status': 'Final'}
    )
    
    Activity.objects.get_or_create(
        log=log,
        task=task_irrigation,
        crop_plan=plan
    )
    print("✅ Daily Logs and Activities recorded.")

    # 7. Financial Ledger (Initial Capital)
    FinancialLedger.objects.get_or_create(
        farm=farm,
        description='إيداع رأس مال تشغيلي - مزرعة شبوة',
        account_code='1100-CASH',
        defaults={
            'debit': Decimal('10000000.00'),
            'credit': Decimal('0'),
            'is_posted': True
        }
    )
    print("✅ Financial Ledger hardened.")

    # 8. Mass Writeoff Simulation (Axis 18)
    print("⚠️  Simulating Mass Writeoff Event (Axis 18)...")
    
    # 50 trees lost to frost
    BiologicalAssetTransaction.objects.create(
        farm=farm,
        cohort=cohort,
        from_status='PRODUCTIVE',
        to_status='EXCLUDED',
        quantity=50,
        notes='ظاهرة صقيع مفاجئة - عتق'
    )
    print("✅ Mass Writeoff recorded and cascaded to stocks.")

    print("\n🏁 Operation Sovereign Finality: Shabwah Simulation Complete! 🏁")

if __name__ == "__main__":
    seed_shabwah()
