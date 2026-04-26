import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()
from decimal import Decimal
from smart_agri.core.models import (
    CropPlan, CropPlanLocation, Farm, Crop, Location, Season,
)

farm = Farm.objects.get(id=28)
season = Season.objects.get(name='موسم 2026')
print(f'Farm: {farm.name} | Season: {season.name}')

# Get first location for this farm
locations = list(Location.objects.filter(farm=farm))
if not locations:
    loc = Location.objects.create(farm=farm, name='القسم الرئيسي', code='SEC-01')
    locations = [loc]
    print(f'Created Location: {loc.name}')
else:
    print(f'Locations: {", ".join(l.name for l in locations)}')

loc = locations[0]  # Use first location for all plans

# Get our 3 crops
crops = {c.name: c for c in Crop.objects.filter(name__in=['المانجو', 'الموز', 'القمح'])}
print(f'Crops found: {list(crops.keys())}')

plans_data = [
    {
        'crop': crops['المانجو'],
        'name': 'خطة المانجو — مزرعة سردود — 2026',
        'start': '2026-01-01', 'end': '2026-12-31',
        'budget_materials': Decimal('50000.0000'),
        'budget_labor': Decimal('30000.0000'),
        'budget_machinery': Decimal('10000.0000'),
        'budget_total': Decimal('90000.0000'),
        'expected_yield': Decimal('5000.00'),
        'yield_unit': 'كغ',
    },
    {
        'crop': crops['الموز'],
        'name': 'خطة الموز — مزرعة سردود — 2026',
        'start': '2026-01-01', 'end': '2026-12-31',
        'budget_materials': Decimal('40000.0000'),
        'budget_labor': Decimal('25000.0000'),
        'budget_machinery': Decimal('8000.0000'),
        'budget_total': Decimal('73000.0000'),
        'expected_yield': Decimal('8000.00'),
        'yield_unit': 'كغ',
    },
    {
        'crop': crops['القمح'],
        'name': 'خطة القمح — مزرعة سردود — ربيع 2026',
        'start': '2026-03-01', 'end': '2026-08-31',
        'budget_materials': Decimal('20000.0000'),
        'budget_labor': Decimal('15000.0000'),
        'budget_machinery': Decimal('12000.0000'),
        'budget_total': Decimal('47000.0000'),
        'expected_yield': Decimal('3000.00'),
        'yield_unit': 'كغ',
    },
]

from smart_agri.core.constants import CropPlanStatus

for pd in plans_data:
    plan, created = CropPlan.objects.get_or_create(
        farm=farm,
        crop=pd['crop'],
        name=pd['name'],
        defaults={
            'start_date': pd['start'],
            'end_date': pd['end'],
            'season': season,
            'budget_materials': pd['budget_materials'],
            'budget_labor': pd['budget_labor'],
            'budget_machinery': pd['budget_machinery'],
            'budget_total': pd['budget_total'],
            'budget_amount': pd['budget_total'],
            'expected_yield': pd['expected_yield'],
            'yield_unit': pd['yield_unit'],
            'status': CropPlanStatus.ACTIVE,
            'currency': 'YER',
        }
    )
    action = 'NEW' if created else 'EXISTS'
    print(f'CropPlan: {plan.name} (id={plan.id}) [{action}]')

    # Link location to plan
    cpl, cpl_created = CropPlanLocation.objects.get_or_create(
        crop_plan=plan,
        location=loc,
        defaults={'assigned_area': Decimal('15.00')}
    )
    print(f'  PlanLocation: {loc.name} (id={cpl.id}) [{"NEW" if cpl_created else "EXISTS"}]')

print('\n=== CROP PLANS SEEDED ===')
