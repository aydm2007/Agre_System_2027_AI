import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")

import django
django.setup()

from smart_agri.finance.models import FinancialLedger
from smart_agri.sales.models import SalesInvoice

def run():
    print("--- Sales Invoices ---")
    invoices = SalesInvoice.objects.all().order_by('-id')[:5]
    for inv in invoices:
        print(f"Invoice {inv.invoice_number}: Total={inv.total_amount}, Status={inv.status}")

    print("\n--- Financial Ledger Entries ---")
    entries = FinancialLedger.objects.all().order_by('-id')[:10]
    for e in entries:
        print(f"{e.id} | {e.created_at.date()} | {e.account_code} | {e.description} | DR:{e.debit} | CR:{e.credit}")

if __name__ == "__main__":
    run()
