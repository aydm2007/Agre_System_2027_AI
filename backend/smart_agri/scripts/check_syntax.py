
import os
import sys
import django

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

try:
    from smart_agri.sales.api import SaleViewSet
    print("✅ SaleViewSet imported successfully")
except ImportError as e:
    print(f"❌ ImportError: {e}")
    sys.exit(1)
except (SyntaxError, OSError, ValueError) as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

print("✅ Syntax Check Passed")
