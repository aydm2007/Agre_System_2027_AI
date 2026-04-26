import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")

try:
    import django
    django.setup()
except Exception as e:
    print(f"Failed to setup django: {e}")
    sys.exit(1)

from smart_agri.core.models.hr import Employee
from smart_agri.core.models.log import IdempotencyRecord, DailyLog
from smart_agri.finance.models import FiscalPeriod
from smart_agri.core.models import Farm
from smart_agri.accounts.models import RoleDelegation

try:
    print("Employee check:", list(Employee.objects.values_list('id','category')[:1]))
    print("IdempotencyRecord check:", list(IdempotencyRecord.objects.values_list('id','response_status','response_body')[:1]))
    print("DailyLog check:", list(DailyLog.objects.values_list('id','variance_status')[:1]))
    print("FiscalPeriod check:", list(FiscalPeriod.objects.values_list('id','status')[:1]))
    print("Farm check:", list(Farm.objects.values_list('id','tier')[:1]))
    print("RoleDelegation table:", RoleDelegation.objects.model._meta.db_table)
except Exception as e:
    print(f"Db Probe Failed: {e}")
    sys.exit(1)

print("ALL AXIS 1 PROBES PASSED")
