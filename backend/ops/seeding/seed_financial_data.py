"""
[AGRI-GUARDIAN] Seed Essential Financial Data
Seeds BudgetClassification entries and SectorRelationship records
needed for the complete document cycle.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from decimal import Decimal
from smart_agri.finance.models import (
    BudgetClassification,
    SectorRelationship,
    CostConfiguration,
)
from smart_agri.core.models.farm import Farm

# ─── Budget Classifications (دليل بنود الموازنة) ───
BUDGET_CODES = [
    ("1100", "رواتب وأجور (مسؤولون)"),
    ("1200", "رواتب وأجور (عمال عقود)"),
    ("2111", "وقود ومحروقات (ديزل)"),
    ("2112", "وقود ومحروقات (بنزين)"),
    ("2200", "مبيدات وأسمدة"),
    ("2300", "بذور ومستلزمات زراعية"),
    ("2400", "أعلاف ومنتجات حيوانية"),
    ("3100", "صيانة آليات ومعدات"),
    ("3200", "صيانة شبكات ري"),
    ("3300", "صيانة مباني ومنشآت"),
    ("4100", "مصاريف نقل وترحيل"),
    ("4200", "مصاريف كهرباء وطاقة"),
    ("4300", "مصاريف اتصالات"),
    ("5100", "إيجارات أراضي وعقارات"),
    ("5200", "عقود مقاولين"),
    ("6100", "مشتريات أصول (آليات)"),
    ("6200", "مشتريات أصول (أثاث ومعدات)"),
    ("7100", "رسوم حكومية وزكاة"),
    ("8100", "مصاريف إدارية متنوعة"),
]

print("=" * 60)
print("  [AGRI-GUARDIAN] Seeding Financial Data")
print("=" * 60)

# Create Budget Classifications
created_bc = 0
for code, name in BUDGET_CODES:
    obj, created = BudgetClassification.objects.get_or_create(
        code=code,
        defaults={"name_ar": name, "is_active": True},
    )
    if created:
        created_bc += 1
        print(f"  ✅ BudgetClassification: {code} - {name}")
    else:
        print(f"  ⏭️  Already exists: {code} - {name}")

print(f"\n  Created {created_bc} new BudgetClassification entries")

# ─── Sector Relationships ───
farms = Farm.objects.filter(deleted_at__isnull=True)
created_sr = 0
for farm in farms:
    obj, created = SectorRelationship.objects.get_or_create(
        farm=farm,
        defaults={
            "current_balance": Decimal("0.0000"),
            "allow_revenue_recycling": False,
        },
    )
    if created:
        created_sr += 1
        print(f"  ✅ SectorRelationship: {farm.name}")
    else:
        print(f"  ⏭️  Already exists: {farm.name}")

print(f"\n  Created {created_sr} new SectorRelationship entries")

# ─── Cost Configurations ───
created_cc = 0
for farm in farms:
    if not CostConfiguration.objects.filter(farm=farm).exists():
        CostConfiguration.objects.create(
            farm=farm,
            daily_labor_rate=Decimal("3000.0000"),  # 3000 YER per Surra
            fuel_price_per_liter=Decimal("500.0000"),  # 500 YER/L
            currency="YER",
        )
        created_cc += 1
        print(f"  ✅ CostConfiguration: {farm.name}")
    else:
        print(f"  ⏭️  Already exists: {farm.name}")

print(f"\n  Created {created_cc} new CostConfiguration entries")
print("\n" + "=" * 60)
print(f"  TOTAL: {created_bc} budgets, {created_sr} sector rels, {created_cc} cost configs")
print("=" * 60)
