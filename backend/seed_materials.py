import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.inventory.models import Item, Unit
from smart_agri.core.models import Crop, Farm, CropMaterial
from decimal import Decimal

def seed_materials():
    print("Seeding missing agricultural materials...")
    farm = Farm.objects.filter(slug='sardood-farm').first()
    if not farm:
         print("Sardood farm not found.")
         return

    unit_kg, _ = Unit.objects.get_or_create(code='KG', defaults={'name': 'Kilogram'})
    unit_l, _ = Unit.objects.get_or_create(code='L', defaults={'name': 'Liter'})

    materials = [
        {'code': 'FERT-UREA-01', 'name': 'سماد يوريا 46%', 'group': 'أسمدة', 'unit': unit_kg, 'type': 'FERTILIZER', 'cost': '150'},
        {'code': 'FERT-COMP-01', 'name': 'سماد عضوي (دمن)', 'group': 'أسمدة', 'unit': unit_kg, 'type': 'FERTILIZER', 'cost': '50'},
        {'code': 'PEST-FUNG-01', 'name': 'مبيد فطري كبريتي', 'group': 'مبيدات', 'unit': unit_l, 'type': 'PESTICIDE', 'cost': '250'},
    ]

    items = []
    for m in materials:
        item, _ = Item.objects.get_or_create(
            name=m['name'],
            group=m['group'],
            defaults={
                'material_type': m['type'],
                'unit': m['unit'],
                'unit_price': Decimal(m['cost']),
            }
        )
        items.append((item, m['type']))

    # Link to crops (Mango, Banana, Wheat, Corn)
    crops = Crop.objects.filter(name__in=['مانجو', 'موز', 'قمح', 'ذرة صفراء'])
    for c in crops:
        for item, mat_type in items:
            CropMaterial.objects.get_or_create(
                crop=c,
                item=item,
                defaults={}
            )
    print("Materials seeded and linked successfully.")

if __name__ == '__main__':
    seed_materials()
