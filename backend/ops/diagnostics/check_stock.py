import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models.tree import LocationTreeStock

print("=== ALL TREE STOCK ===")
for s in LocationTreeStock.objects.all()[:20]:
    print(f"ID: {s.id}, Variety: {s.crop_variety.name}, Crop: {s.crop_variety.crop.name}, Location: {s.location.name}, Count: {s.current_tree_count}")
