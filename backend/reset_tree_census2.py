import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.db import transaction
from smart_agri.core.models.inventory import BiologicalAssetCohort

def reset_tree_census_completely():
    with transaction.atomic():
        # Soft delete all initial tree census records (Cohorts)
        cohorts = BiologicalAssetCohort.objects.filter(deleted_at__isnull=True)
        count = cohorts.count()
        
        from django.utils import timezone
        now = timezone.now()
        
        cohorts.update(deleted_at=now)
        
        print(f"Successfully soft-deleted {count} BiologicalAssetCohort records (Tree Census data).")
        
if __name__ == "__main__":
    reset_tree_census_completely()
