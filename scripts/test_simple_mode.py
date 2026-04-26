import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from decimal import Decimal
from django.utils import timezone
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import SystemSettings
from smart_agri.core.services.daily_log_execution import FrictionlessDailyLogService
from smart_agri.finance.models import FinancialLedger

def test_simple_mode():
    farm = Farm.objects.filter(is_active=True).first()
    if not farm:
        print("No active farm found.")
        return

    # Ensure SIMPLE mode
    settings = SystemSettings.get_settings()
    settings.strict_erp_mode = False
    settings.save()

    print(f"Testing SIMPLE mode on Farm: {farm.name}")
    print(f"Strict ERP Mode: {settings.strict_erp_mode}")

    log_date = timezone.now().date()
    # Execute frictionless log
    result = FrictionlessDailyLogService.process_technical_log(
        farm=farm,
        log_date=log_date,
        activity_name="Test SIMPLE Mode Activity",
        workers_count=2,
        shift_hours=Decimal('8.0'),
    )

    log_id = result['daily_log_id']
    print(f"Daily Log created successfully. ID: {log_id}")

    # Check shadow ledger entries
    ledger_entries = FinancialLedger.objects.filter(
        analytical_tags__daily_log_id=log_id
    )
    
    print(f"Shadow Ledger Entries Found: {ledger_entries.count()}")
    for entry in ledger_entries:
        print(f" - {entry.account_code} | DR: {entry.debit} | CR: {entry.credit} | Tags: {entry.analytical_tags}")

if __name__ == '__main__':
    test_simple_mode()
