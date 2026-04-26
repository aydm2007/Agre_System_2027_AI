import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

django.setup()

from smart_agri.core.models.inventory import BiologicalAssetCohort
from smart_agri.core.models.tree import LocationTreeStock

cohorts = BiologicalAssetCohort.objects.all()
created_count = 0
for cohort in cohorts:
    if getattr(cohort, 'deleted_at', None) is not None:
        continue
    if cohort.status not in [ 
        BiologicalAssetCohort.STATUS_JUVENILE,
        BiologicalAssetCohort.STATUS_PRODUCTIVE,
        BiologicalAssetCohort.STATUS_SICK,
        BiologicalAssetCohort.STATUS_RENEWING,
    ]:
        continue
    if not cohort.variety:
        continue

    stock, created = LocationTreeStock.objects.get_or_create(
        location=cohort.location,
        crop_variety=cohort.variety,
        defaults={'current_tree_count': 0}
    )
    if created:
        created_count += 1
    elif stock.deleted_at is not None:
        stock.deleted_at = None
        stock.save(update_fields=['deleted_at'])
        created_count += 1

print(f"Synced {created_count} previous cohorts silently.")
