import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.models import Crop, Farm, CropProduct, FarmCrop
from smart_agri.inventory.models import Item, Unit
from smart_agri.core.api.serializers.crop import CropProductSerializer
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

def test_creation():
    # [AG-CLEANUP] print("Testing CropProduct creation with implicit name...")
    
    # Setup Data
    farm = Farm.objects.first()
    if not farm:
        # [AG-CLEANUP] print("No farms found.")
        return

    crop, _ = Crop.objects.get_or_create(name="Test Crop For Product")
    FarmCrop.objects.get_or_create(farm=farm, crop=crop)
    
    unit, _ = Unit.objects.get_or_create(code="KG", defaults={"name": "Kilogram"})
    item, _ = Item.objects.get_or_create(
        name="Test Fertilizer", 
        defaults={"group": "Material", 'uom': 'kg', "unit": unit}
    )

    # Simulate Request
    factory = APIRequestFactory()
    request = factory.post('/')
    request.user = type('User', (object,), {'is_superuser': True, 'is_authenticated': True})()

    data = {
        "crop": crop.id,
        "item": item.id,
        "farm": farm.id
    }

    serializer = CropProductSerializer(data=data, context={'request': request})
    if serializer.is_valid():
        # [AG-CLEANUP] print("Serializer is valid.")
        product = serializer.save()
        # [AG-CLEANUP] print(f"Created Product: {product.name} (ID: {product.id})")
        # [AG-CLEANUP] print(f"Product Name matches Item Name: {product.name == item.name}")
        
        # Cleanup
        product.delete()
        crop.delete()
        item.delete()
    else:
        pass # [AG-FIX]
        # [AG-CLEANUP] print("Serializer errors:", serializer.errors)

if __name__ == "__main__":
    test_creation()
