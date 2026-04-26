import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.config.settings")
django.setup()

from smart_agri.core.models.inventory import BiologicalAssetCohort
from smart_agri.core.models.tree import LocationTreeStock

cohort = BiologicalAssetCohort.objects.last()
if cohort:
    print(f"Testing save on cohort {cohort.id} (Status: {cohort.status})")
    print("Stock count before:", LocationTreeStock.objects.filter(location=cohort.location, crop_variety=cohort.variety).count())
    cohort.save()
    print("Stock count after:", LocationTreeStock.objects.filter(location=cohort.location, crop_variety=cohort.variety).count())
else:
    print("No cohorts found.")
