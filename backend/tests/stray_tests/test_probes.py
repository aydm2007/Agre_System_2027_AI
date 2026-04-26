import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

import sys

def run_probes():
    print("Running Mandatory Runtime Probes...")
    try:
        from smart_agri.core.models.hr import Employee
        print("Employee Probe:", list(Employee.objects.values_list('id','category')[:1]))
    except Exception as e:
        print("Employee Probe FAILED:", e)

    try:
        from smart_agri.core.models.log import IdempotencyRecord
        print("IdempotencyRecord Probe:", list(IdempotencyRecord.objects.values_list('id','response_status','response_body')[:1]))
    except Exception as e:
        print("IdempotencyRecord Probe FAILED:", e)

    try:
        from smart_agri.core.models.log import DailyLog
        print("DailyLog Probe:", list(DailyLog.objects.values_list('id','variance_status')[:1]))
    except Exception as e:
        print("DailyLog Probe FAILED:", e)

    try:
        from smart_agri.finance.models import FiscalPeriod
        print("FiscalPeriod Probe:", list(FiscalPeriod.objects.values_list('id','status')[:1]))
    except Exception as e:
        print("FiscalPeriod Probe FAILED:", e)

    try:
        from smart_agri.core.models import Farm
        print("Farm Probe:", list(Farm.objects.values_list('id','tier')[:1]))
    except Exception as e:
        print("Farm Probe FAILED:", e)

    try:
        from smart_agri.accounts.models import RoleDelegation
        print("RoleDelegation table exists:", RoleDelegation.objects.model._meta.db_table)
    except Exception as e:
        print("RoleDelegation Probe FAILED:", e)

if __name__ == '__main__':
    run_probes()
