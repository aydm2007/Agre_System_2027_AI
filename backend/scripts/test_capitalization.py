import os
import sys
import django
from decimal import Decimal

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.utils import timezone
from smart_agri.core.models.farm import Farm, Location
from smart_agri.core.models.crop import Crop, CropVariety
from smart_agri.core.models.inventory import BiologicalAssetCohort
from smart_agri.core.models.activity import Activity
from smart_agri.finance.models import FinancialLedger
from smart_agri.finance.services.core_finance import FinanceService

def run_test():
    farm = Farm.objects.filter(deleted_at__isnull=True).first()
    if not farm:
        print("No farm found.")
        return

    location = Location.objects.filter(farm=farm).first()
    if not location:
        print("No location found.")
        return

    crop, _ = Crop.objects.get_or_create(name="Test Asset Crop")
    variety, _ = CropVariety.objects.get_or_create(crop=crop, name="Test Asset Variety")

    # Clean old cohorts & ledgers for this specific test
    BiologicalAssetCohort.objects.filter(crop=crop).delete()
    
    # Create JUVENILE Cohort
    juv_cohort = BiologicalAssetCohort.objects.create(
        farm=farm,
        location=location,
        crop=crop,
        variety=variety,
        batch_name="Juv_Test_Caps",
        status=BiologicalAssetCohort.STATUS_JUVENILE,
        quantity=100,
        planted_date=timezone.now().date()
    )
    print(f"Created JUVENILE Cohort: {juv_cohort.id}")

    # 1. Test JUVENILE Activity (Should goto WIP)
    activity_juv = Activity.objects.create(
        location=location,
        crop=crop,
        crop_variety=variety,
        cost_total=Decimal("1500.0000"),
        activity_date=timezone.now().date()
    )
    FinanceService.sync_activity_ledger(activity_juv, user=None)
    
    # Verify WIP
    wip_entries = FinancialLedger.objects.filter(activity=activity_juv, account_code=FinancialLedger.ACCOUNT_WIP)
    if wip_entries.exists() and wip_entries.first().debit == Decimal("1500.0000"):
        print("✅ JUVENILE Cost correctly capitalized to WIP account.")
    else:
        print("❌ FAILED: JUVENILE Cost not in WIP.")

    # Clear cohorts again to isolate PRODUCTIVE test
    BiologicalAssetCohort.objects.filter(crop=crop).delete()
    
    # Create PRODUCTIVE Cohort
    prod_cohort = BiologicalAssetCohort.objects.create(
        farm=farm,
        location=location,
        crop=crop,
        variety=variety,
        batch_name="Prod_Test_Caps",
        status=BiologicalAssetCohort.STATUS_PRODUCTIVE,
        quantity=100,
        planted_date=timezone.now().date()
    )
    print(f"Created PRODUCTIVE Cohort: {prod_cohort.id}")

    # 2. Test PRODUCTIVE Activity (Should goto MATERIAL)
    activity_prod = Activity.objects.create(
        location=location,
        crop=crop,
        crop_variety=variety,
        cost_total=Decimal("2000.0000"),
        activity_date=timezone.now().date()
    )
    FinanceService.sync_activity_ledger(activity_prod, user=None)
    
    # Verify MATERIAL
    mat_entries = FinancialLedger.objects.filter(activity=activity_prod, account_code=FinancialLedger.ACCOUNT_MATERIAL)
    if mat_entries.exists() and mat_entries.first().debit == Decimal("2000.0000"):
        print("✅ PRODUCTIVE Cost correctly expensed to MATERIAL account.")
    else:
        print("❌ FAILED: PRODUCTIVE Cost not in MATERIAL.")

    # 3. Test Reversals
    FinanceService.reverse_activity_ledger(activity_juv, user=None)
    FinanceService.reverse_activity_ledger(activity_prod, user=None)
    print("✅ Reversals executed. Check database for ledger credits.")
    
if __name__ == '__main__':
    run_test()
