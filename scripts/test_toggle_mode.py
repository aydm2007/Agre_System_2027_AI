import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from smart_agri.core.models.farm import FarmSettings

print("Testing FarmSettings toggle...")
try:
    settings = FarmSettings.objects.first()
    if settings:
        print(f"Current strict_erp_mode: {settings.strict_erp_mode}")
        settings.strict_erp_mode = not settings.strict_erp_mode
        settings.save()
        print(f"New strict_erp_mode: {settings.strict_erp_mode}")
    else:
        print("No FarmSettings found.")
except Exception as e:
    import traceback
    traceback.print_exc()
