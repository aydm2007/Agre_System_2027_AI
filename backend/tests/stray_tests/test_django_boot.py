import os
import sys

print("Initializing environment...", flush=True)

try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
    django.setup()
    print("Django setup complete.", flush=True)
    
    from smart_agri.core.models import Farm
    count = Farm.objects.count()
    print(f"Farm count: {count}", flush=True)

    with open('test_django_boot.txt', 'w') as f:
        f.write(f"Boot success! Farms: {count}\n")
        
except Exception as e:
    print(f"Error: {e}", file=sys.stderr, flush=True)
