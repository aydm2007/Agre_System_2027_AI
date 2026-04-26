"""
Agri-Guardian Database Cleanup Command
Scans and removes test data entries (Test, Verify) from the database
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from smart_agri.core.models import Farm, Crop, FarmCrop, Activity, Task


class Command(BaseCommand):
    help = 'Scan and cleanup test data from database (Test, Verify patterns)'

    TEST_PATTERNS = ['test', 'verify', 'TEST', 'VERIFY', 'Test', 'Verify', 'تجربة', 'اختبار', 'فحص']

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only scan, do not delete any data',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Actually delete test data (USE WITH CAUTION)',
        )

    def is_test_data(self, name):
        """Check if a name matches test patterns"""
        if not name:
            return False
        name_lower = str(name).lower()
        return any(p.lower() in name_lower for p in self.TEST_PATTERNS)

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', True)
        delete_mode = options.get('delete', False)

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.WARNING("AGRI-GUARDIAN DATABASE CLEANUP"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Mode: {'DRY RUN (scan only)' if dry_run or not delete_mode else 'DELETE MODE'}")
        self.stdout.write("")

        # Scan Farms
        self.stdout.write(self.style.HTTP_INFO("\n=== FARMS ==="))
        test_farms = []
        ok_farms = []
        for farm in Farm.objects.all():
            if self.is_test_data(farm.name):
                test_farms.append(farm)
                self.stdout.write(self.style.ERROR(f"  [TEST] ID: {farm.id}, Name: {farm.name}"))
            else:
                ok_farms.append(farm)
                self.stdout.write(self.style.SUCCESS(f"  [OK]   ID: {farm.id}, Name: {farm.name}"))

        # Scan Crops
        self.stdout.write(self.style.HTTP_INFO("\n=== CROPS ==="))
        test_crops = []
        ok_crops = []
        for crop in Crop.objects.all():
            # Get farm names via FarmCrop
            farm_links = FarmCrop.objects.filter(crop=crop).select_related('farm')
            farm_names = ', '.join([fc.farm.name for fc in farm_links]) if farm_links.exists() else 'No Farm'
            
            if self.is_test_data(crop.name):
                test_crops.append(crop)
                self.stdout.write(self.style.ERROR(f"  [TEST] ID: {crop.id}, Name: {crop.name}, Farms: {farm_names}"))
            else:
                ok_crops.append(crop)
                self.stdout.write(self.style.SUCCESS(f"  [OK]   ID: {crop.id}, Name: {crop.name}, Farms: {farm_names}"))

        # Scan Tasks
        self.stdout.write(self.style.HTTP_INFO("\n=== TASKS ==="))
        test_tasks = []
        for task in Task.objects.all():
            if self.is_test_data(task.name):
                test_tasks.append(task)
                self.stdout.write(self.style.ERROR(f"  [TEST] ID: {task.id}, Name: {task.name}"))
        self.stdout.write(f"  Total Tasks: {Task.objects.count()}, Test Tasks: {len(test_tasks)}")

        # Scan Activities - count activities related to test entities
        self.stdout.write(self.style.HTTP_INFO("\n=== ACTIVITIES ==="))
        
        # Count activities linked to test crops/tasks/farms
        test_crop_ids = [c.id for c in test_crops]
        test_task_ids = [t.id for t in test_tasks]
        test_farm_ids = [f.id for f in test_farms]
        
        # Activities linked to test entities (will be cascade-deleted)
        test_activities_by_crop = Activity.objects.filter(crop_id__in=test_crop_ids) if test_crop_ids else Activity.objects.none()
        test_activities_by_task = Activity.objects.filter(task_id__in=test_task_ids) if test_task_ids else Activity.objects.none()
        
        self.stdout.write(f"  Activities linked to test crops: {test_activities_by_crop.count()}")
        self.stdout.write(f"  Activities linked to test tasks: {test_activities_by_task.count()}")
        total_activities = Activity.objects.count()
        self.stdout.write(f"  Total Activities: {total_activities}")

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("SUMMARY"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Test Farms Found: {len(test_farms)}")
        self.stdout.write(f"Test Crops Found: {len(test_crops)}")
        self.stdout.write(f"Test Tasks Found: {len(test_tasks)}")
        self.stdout.write(f"Activities to be deleted (linked to test data): {test_activities_by_crop.count() + test_activities_by_task.count()}")

        # Delete if requested
        if delete_mode and not dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️ DELETING TEST DATA..."))
            
            with transaction.atomic():
                # Delete in correct order (dependencies first)
                
                # Delete activities linked to test crops first
                crop_activity_count = test_activities_by_crop.count()
                if crop_activity_count > 0:
                    test_activities_by_crop.delete()
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Deleted {crop_activity_count} activities linked to test crops"))
                
                # Delete test tasks
                for task in test_tasks:
                    # First delete related activities
                    Activity.objects.filter(task_id=task.id).delete()
                    task.delete()
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Deleted task: {task.name}"))
                
                # Delete test crops (and related activities)
                for crop in test_crops:
                    # Delete related activities first
                    Activity.objects.filter(crop_id=crop.id).delete()
                    # Delete FarmCrop links
                    FarmCrop.objects.filter(crop=crop).delete()
                    crop.delete()
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Deleted crop: {crop.name}"))
                
                # Delete test farms (and all related entities)
                for farm in test_farms:
                    # Delete all FarmCrop links for this farm
                    FarmCrop.objects.filter(farm=farm).delete()
                    # Farm deletion should cascade to related entities via Django FK
                    farm.delete()
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Deleted farm: {farm.name}"))

            self.stdout.write(self.style.SUCCESS("\n✅ CLEANUP COMPLETE"))
        else:
            self.stdout.write(self.style.NOTICE("\nℹ️  DRY RUN - No data was deleted"))
            self.stdout.write("To delete, run with: python manage.py cleanup_test_data --delete")

