import os
import django
import sys
from decimal import Decimal
from django.utils import timezone

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.core.models import (
    Farm, CropPlan, CropPlanBudgetLine, Task, Activity, ActivityItem, 
    DailyLog, Item, Unit, Season, Location, Crop, ActivityHarvest, CropProduct
)
from smart_agri.core.models.settings import Supervisor
from smart_agri.finance.models import CostConfiguration

from django.contrib.auth import get_user_model

User = get_user_model()

def run():
    print("\n=======================================================")
    print("   [ دَورَةْ خُطَطِ المَحَاصِيلِ وَالمِيزَانِيَة ]    ")
    print("   [ Crop Plan & Budget Simulation Cycle ]      ")
    print("=======================================================\n")

    # 1. Fetch Farm and Manager
    farm = Farm.objects.filter(name="مزرعة الجروبة").first()
    if not farm:
        print("❌ Error: مزرعة الجروبة not found. Please run setup_farms_and_cycles.py first.")
        return

    manager = User.objects.filter(groups__name="مدير المزرعة").first()
    if not manager:
        manager = User.objects.first()

    # Create/Get Configuration with 10% Warning and 20% Critical Thresholds
    CostConfiguration.objects.get_or_create(
        farm=farm,
        defaults={
            "variance_warning_pct": Decimal("10.00"),
            "variance_critical_pct": Decimal("20.00"),
            "overhead_per_hectare": Decimal("5000.00")
        }
    )

    # 1. Budgeting stage (Creation of Crop Plan with Standards)
    print(">>> [المرحلة 1] إعداد الخطة الزراعية والموازنة المعتمدة (Budgeting) <<<")
    season, _ = Season.objects.get_or_create(name="موسم 2026", defaults={"start_date": timezone.now().date(), "end_date": timezone.now().date()})
    crop, _ = Crop.objects.get_or_create(name="موز الجروبة", mode="Perennial")
    location, _ = Location.objects.get_or_create(farm=farm, name="حقل رقم 1", defaults={"type": "Field"})
    
    plan, created = CropPlan.objects.get_or_create(
        farm=farm,
        season=season,
        crop=crop,
        location=location,
        defaults={
            "name": "الخطة الشتوية 2026 - موز",
            "start_date": timezone.now().date(),
            "end_date": timezone.now().date(),
            "currency": "YER",
            "expected_yield": Decimal("2000.00"),  # Expected to harvest 2000 units
            "yield_unit": "KG",
            "budget_materials": Decimal("50000.00"),
            "budget_labor": Decimal("20000.00"),
            "budget_machinery": Decimal("30000.00"),
            "budget_total": Decimal("100000.00")
        }
    )

    if not created:
        plan.expected_yield = Decimal("2000.00")
        plan.budget_materials = Decimal("50000.00")
        plan.budget_labor = Decimal("20000.00")
        plan.budget_machinery = Decimal("30000.00")
        plan.budget_total = Decimal("100000.00")
        plan.save()

    print(f"✅ تم إصدار الخطة: {plan.name}")
    print(f"   الكمية المستهدفة (Harvest Target): {plan.expected_yield} {plan.yield_unit}")
    print(f"   الميزانية المعتمدة (Total Budget): {plan.budget_total} YER")
    print(f"   - مواد: {plan.budget_materials} | عمالة: {plan.budget_labor} | آلات: {plan.budget_machinery}\n")

    task_fert, _ = Task.objects.get_or_create(name="تسميد عضوي")
    task_harv, _ = Task.objects.get_or_create(name="حصاد")

    CropPlanBudgetLine.objects.get_or_create(
        crop_plan=plan, task=task_fert, category="materials",
        defaults={"total_budget": Decimal("40000.00")}
    )

    # 2. Execution Phase (Posting Actuals)
    print(">>> [المرحلة 2] تسجيل العمليات الفعلية (Execution & Actuals) <<<")
    
    # Let's overshoot the budget to simulate a warning/critical variance.
    # Total actual materials will be 58,000 (Warning -> 16% variance) or 65,000 (Critical -> 30% variance)
    fertilizer, _ = Item.objects.get_or_create(name="سماد البوتاسيوم", defaults={"group": "FERTILIZER"})
    
    supervisor, _ = Supervisor.objects.get_or_create(farm=farm, name=manager.username)
    
    log, _ = DailyLog.objects.get_or_create(
        farm=farm, log_date=timezone.now().date(), supervisor=supervisor, status="DRAFT"
    )
    
    # We will simulate the cost directly into the Activity summary since CostingEngine needs full transaction setups
    act = Activity.objects.create(
        log=log, crop_plan=plan, location=location, task=task_fert,
        note="عملية تسميد فعلية (تجاوز للموازنة)", created_by=manager,
        cost_materials=Decimal("65000.00"), # 30% over 50,000 budget! -> CRITICAL
        cost_labor=Decimal("20000.00"),
        cost_machinery=Decimal("30000.00"),
        cost_total=Decimal("115000.00")     # 15% over 100,000 budget -> WARNING
    )
    print(f"✅ عملية مجدولة مسجلة بتكلفة (Materials Cost): {act.cost_materials} YER (موازنة المواد = {plan.budget_materials})")
    print(f"✅ إجمالي التكلفة للفترة (Total Cost): {act.cost_total} YER (الموازنة الكلية = {plan.budget_total})\n")

    # Let's simulate Harvest (Under-yield to simulate CRITICAL yield variance)
    # Expected yield = 2000, Actual Yield = 1300 (35% deviation -> CRITICAL)
    print(">>> [المرحلة 3] تسجيل حصيلة الإنتاج (Yield Entry) <<<")
    act_harv = Activity.objects.create(
        log=log, crop_plan=plan, location=location, task=task_harv, 
        note="حصاد فعلي (نقص عن المتوقع)", created_by=manager,
        cost_materials=Decimal("0.00"), cost_labor=Decimal("0.00"), cost_machinery=Decimal("0.00"), cost_total=Decimal("0.00")
    )
    prod, _ = CropProduct.objects.get_or_create(crop=crop, is_primary=True, item=fertilizer) # Using generic item for mock
    ActivityHarvest.objects.create(
        activity=act_harv,
        harvest_quantity=Decimal("1300.00") # 35% less than 2000
    )
    print(f"✅ الكمية المحصودة (Actual Yield): 1300.00 {plan.yield_unit} (المستهدف = {plan.expected_yield} {plan.yield_unit})\n")

    # 3. Variance & Control Reporting
    print(">>> [المرحلة 4] تدقيق المعايير والانحرافات (Variance Control Check) <<<")
    from smart_agri.core.services.variance import compute_plan_variance, compute_material_variance, compute_yield_variance

    mat_var = compute_material_variance(plan.pk)
    print("1. [انحراف المواد (Material Variance)]:")
    for cat in mat_var['categories']:
        if cat['category'] == 'materials':
            print(f"   الخطة: {cat['budget']} | الفعلي: {cat['actual']} | التجاوز: {cat['deviation_pct']}% | الحالة: [{cat['status']}]")

    yield_var = compute_yield_variance(plan.pk)
    print("2. [انحراف الإنتاجية (Yield Variance)]:")
    print(f"   الخطة: {yield_var['expected_yield']} | الفعلي: {yield_var['actual_yield']} | النقص: {abs(yield_var['deviation_pct'])}% | الحالة: [{yield_var['status']}]")

    print("\n=======================================================")
    print("   [ الدورة تمت بنجاح - Simulation Complete ]    ")
    print("=======================================================\n")


if __name__ == "__main__":
    run()
