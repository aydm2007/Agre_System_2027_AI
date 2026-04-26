import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.db import transaction
from smart_agri.core.models import Activity, LocationTreeStock, Task

def reset_tree_census():
    with transaction.atomic():
        stocks = list(LocationTreeStock.objects.all())
        reset_count = 0
        for stock in stocks:
            if stock.current_tree_count != stock.initial_tree_count:
                stock.current_tree_count = stock.initial_tree_count
                stock.save(update_fields=['current_tree_count'])
                reset_count += 1
                
        # To completely erase the "Actual Tree Census" that was input:
        # We need to find the activities that belong to the TREE_CENSUS archetype.
        # If archetype is not available or not strictly set, we can delete all activities
        # where there was a tree adjustment OR it's a specific task name. 
        # Usually, checking tree_count_delta != 0 and tree_loss_reason=None helps narrow down
        # biological adjustments vs normal deaths. But since the user wants to *reset the census*, 
        # deleting every activity that has a non-zero tree_count_delta is a safe reset of tree inventory edits.
        
        # Let's delete activities that adjusted trees.
        activities_to_delete = Activity.objects.filter(
            deleted_at__isnull=True
        ).exclude(tree_count_delta=0)
        
        deleted_count = activities_to_delete.count()
        
        from django.utils import timezone
        now = timezone.now()
        activities_to_delete.update(deleted_at=now)
        
        print(f"Reset {reset_count} LocationTreeStock records to initial_tree_count.")
        print(f"Soft deleted {deleted_count} stock adjustment activities.")

if __name__ == "__main__":
    reset_tree_census()
