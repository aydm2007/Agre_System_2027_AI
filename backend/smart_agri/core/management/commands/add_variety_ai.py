from django.core.management.base import BaseCommand
from smart_agri.core.models.farm import Farm, Location, Task
from smart_agri.core.models.crop import Crop, CropVariety
from smart_agri.core.models.activity import DailyLog, Activity
from smart_agri.core.models.tree import LocationTreeStock
from smart_agri.core.services.inventory.service import TreeInventoryService
from django.contrib.auth import get_user_model
from django.utils import timezone

class Command(BaseCommand):
    help = 'Adds a perennial crop, a new variety, and links it to a location via TreeInventoryService.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting AI injection script..."))
        
        try:
            User = get_user_model()
            admin_user = User.objects.filter(is_superuser=True).first()

            farm = Farm.objects.filter(name__icontains="سردود").first() or Farm.objects.first()
            if not farm:
                self.stdout.write(self.style.ERROR("No farm found!"))
                return

            location = Location.objects.filter(farm=farm).first()
            if not location:
                self.stdout.write(self.style.ERROR("No location found!"))
                return

            crop, _ = Crop.objects.get_or_create(
                name="رمان",
                defaults={
                    "name_en": "Pomegranate",
                    "is_perennial": True,
                    "category": "FRUIT",
                    "code": "POM001"
                }
            )

            variety_name = "رمان طائفي"
            variety, created_var = CropVariety.objects.get_or_create(
                crop=crop,
                name=variety_name,
                defaults={
                    "description": "صنف تمت إضافته آلياً بواسطة AI",
                    "is_active": True
                }
            )

            task = Task.objects.filter(name__icontains="زراعة").first()
            if not task:
                self.stdout.write(self.style.ERROR("Planting task not found!"))
                return

            self.stdout.write(self.style.WARNING(f"Preparing to plant {variety.name} in {location.name}..."))
            
            log = DailyLog.objects.create(
                farm=farm,
                log_date=timezone.now().date(),
                supervisor=admin_user,
                status='approved'
            )

            activity = Activity.objects.create(
                log=log,
                location=location,
                task=task,
                crop=crop,
                variety=variety,
                tree_count_delta=200,
                note="Test planting entry by AI Agent for new variety",
                recorded_by=admin_user
            )

            TreeInventoryService.record_event_from_activity(activity=activity)

            stock = LocationTreeStock.objects.filter(location=location, crop_variety=variety).first()
            if stock:
                self.stdout.write(self.style.SUCCESS(f"✅ SUCCESS: Variety '{variety.name}' created under Crop '{crop.name}'. Planted {stock.current_tree_count} trees at Location '{location.name}' in Farm '{farm.name}'."))
            else:
                self.stdout.write(self.style.ERROR("❌ Failed to create LocationTreeStock."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FATAL ERROR: {str(e)}"))
