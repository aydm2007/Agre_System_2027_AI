import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import Item, Unit, CropProduct

print('--- ITEMS (Group Crop) ---')
items = Item.objects.filter(group='Crop')
for item in items:
    print(item.id, item.name, item.group, item.unit)
if not items:
    print('No items with group Crop found')

print('\n--- ALL ITEMS ---')
for item in Item.objects.all()[:5]:
    print(item.id, item.name, item.group)

print('\n--- UNITS ---')
units = Unit.objects.all()
for u in units:
    print(u.id, u.name, u.code)
if not units:
    print('No units found')

print('\n--- CROP PRODUCTS ---')
products = CropProduct.objects.all()
for p in products:
    print(p.id, p.item_id if p.item else None, p.name)
