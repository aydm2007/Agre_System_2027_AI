"""
[AGRI-GUARDIAN] Seed CropProducts for Sales dropdown.
Run: python manage.py seed_crop_products
"""
from django.core.management.base import BaseCommand
from smart_agri.core.models import Crop, CropProduct, Farm
from smart_agri.core.models.crop import FarmCrop


class Command(BaseCommand):
    help = "Seed CropProduct records for the Sales invoice product dropdown"

    def handle(self, *args, **options):
        farms = Farm.objects.filter(deleted_at__isnull=True)
        crops = Crop.objects.filter(deleted_at__isnull=True)

        if not crops.exists():
            self.stdout.write(self.style.WARNING("No crops found. Run seed_full_system first."))
            return

        created_count = 0
        for crop in crops:
            # Create CropProduct for each farm that has this crop
            for farm in farms:
                farm_crop_exists = FarmCrop.objects.filter(
                    farm=farm, crop=crop, deleted_at__isnull=True
                ).exists()

                if farm_crop_exists:
                    product, created = CropProduct.objects.get_or_create(
                        crop=crop,
                        farm=farm,
                        name=f"{crop.name} - {farm.name}",
                        defaults={
                            'is_primary': True,
                            'pack_uom': 'كجم',
                            'reference_price': 100,
                        }
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f"  ✓ CropProduct: {product.name}")

            # Also create a global CropProduct (no farm)
            product, created = CropProduct.objects.get_or_create(
                crop=crop,
                farm=None,
                name=crop.name,
                defaults={
                    'is_primary': False,
                    'pack_uom': 'كجم',
                    'reference_price': 100,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f"  ✓ CropProduct (global): {product.name}")

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Done! Created {created_count} CropProduct records."
        ))
