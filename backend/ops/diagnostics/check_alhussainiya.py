import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import Farm, CropPlan
farms = Farm.objects.filter(name__icontains='الحسينية')
print('Farms:', list(farms.values('id', 'name')))
print('Plans:', list(CropPlan.objects.filter(farm__in=farms).values('id', 'name', 'status')))
