import logging
from django.core.management.base import BaseCommand
from smart_agri.inventory.models import Unit

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Seed Yemeni local units (قدح, ربطة, كيس, سلة)."

    def handle(self, *args, **options):
        units_to_create = [
            {"code": "qadah", "name": "قدح", "symbol": "قدح", "category": Unit.CATEGORY_VOLUME, "precision": 2},
            {"code": "rabta", "name": "ربطة", "symbol": "ربطة", "category": Unit.CATEGORY_COUNT, "precision": 0},
            {"code": "kees", "name": "كيس", "symbol": "كيس", "category": Unit.CATEGORY_COUNT, "precision": 0},
            {"code": "sallah", "name": "سلة", "symbol": "سلة", "category": Unit.CATEGORY_COUNT, "precision": 0},
        ]
        
        for u in units_to_create:
            unit, created = Unit.objects.get_or_create(
                code=u["code"],
                defaults={
                    "name": u["name"],
                    "symbol": u["symbol"],
                    "category": u["category"],
                    "precision": u["precision"],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created unit: {unit.name}"))
            else:
                unit.name = u["name"]
                unit.symbol = u["symbol"]
                unit.save()
                self.stdout.write(self.style.WARNING(f"Unit exists: {unit.name}"))
        
        self.stdout.write(self.style.SUCCESS("Yemeni units seeding complete."))
