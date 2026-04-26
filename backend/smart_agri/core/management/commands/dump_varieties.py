from django.core.management.base import BaseCommand
import json

class Command(BaseCommand):
    help = 'Dump crop varieties response'

    def handle(self, *args, **options):
        from smart_agri.core.models import CropVariety
        from smart_agri.core.api.serializers.crop import CropVarietySerializer
        
        # Simulating farm=1, crop=1, location_ids=1
        variety_location_map = {
            1: {
                "variety_name": "Test",
                "location_ids": [1],
                "available_in_all_locations": True,
                "current_tree_count_total": 100,
                "current_tree_count_by_location": {"1": 100}
            }
        }
        
        # get varieties
        qs = CropVariety.objects.filter(deleted_at__isnull=True)[:5]
        
        context = {"variety_location_map": variety_location_map}
        serializer = CropVarietySerializer(qs, many=True, context=context)
        with open('variety_dump.json', 'w', encoding='utf-8') as f:
            json.dump(serializer.data, f, ensure_ascii=False, indent=2)
        
        print("Dumped to variety_dump.json")
