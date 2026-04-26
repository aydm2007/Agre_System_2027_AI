
import os
import django
from django.conf import settings

# Configure Django settings manually to avoid importing the full settings.py if it causes issues
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
    django.setup()

from smart_agri.core.api.serializers.activity import ActivitySerializer
from smart_agri.core.models import Activity

def check_serializer():
    print("Checking ActivitySerializer configuration...")
    try:
        serializer = ActivitySerializer()
        print("Serializer instantiated successfully.")
        print(f"Model class: {serializer.Meta.model.__name__}")
        print(f"Declared fields: {list(serializer.fields.keys())}")
        
        if 'data' in serializer.fields:
            print("WARNING: 'data' field is present in serializer fields!")
        else:
            print("CONFIRMED: 'data' field is NOT present in serializer fields.")
            
    except Exception as e:
        print(f"ERROR: Serializer configuration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_serializer()
