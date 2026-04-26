import os
import django
import sys
import json

sys.path.append(r"c:\tools\workspace\Agre_ERP_2027-main\backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

from smart_agri.inventory.models import Unit

units = list(Unit.objects.values('id', 'name', 'code')[:20])
with open('units.json', 'w', encoding='utf-8') as f:
    json.dump(units, f, ensure_ascii=False, indent=2)
