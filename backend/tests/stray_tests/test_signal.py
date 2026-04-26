import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.config.settings")
django.setup()

from smart_agri.core.models.inventory import BiologicalAssetCohort
from smart_agri.core.models.tree import LocationTreeStock

print("LocationTreeStock count before:", LocationTreeStock.objects.count())

cohort = BiologicalAssetCohort.objects.last()
if cohort:
    print(f"Last Cohort: {cohort.id}, Farm: {cohort.farm}, Variety: {cohort.variety}, Loc: {cohort.location}, Status: {cohort.status}")
    cohort.save()
    print("LocationTreeStock count after:", LocationTreeStock.objects.count())
else:
    print("No cohorts found.")
