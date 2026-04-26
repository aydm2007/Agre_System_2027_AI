import os
import sys
from decimal import Decimal

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
import django
django.setup()

from smart_agri.core.services.reporting_service import ArabicReportService
from smart_agri.finance.models import FinancialLedger
from smart_agri.core.models.farm import Farm
from django.contrib.auth import get_user_model

try:
    User = get_user_model()
    user, _ = User.objects.get_or_create(username="pdf_tester_runner")
    farm, _ = Farm.objects.get_or_create(name="مزرعة PDF", code="TEST-PDF")
    
    # Revenue
    FinancialLedger.objects.create(
        farm=farm, account_code="4000-REV-PDF", description="إيراد تجريبي",
        credit=Decimal("200000.00"), debit=Decimal("0.00"), created_by=user,
    )
    # Expense
    FinancialLedger.objects.create(
        farm=farm, account_code="7000-EXP-PDF", description="مصروف تجريبي",
        credit=Decimal("0.00"), debit=Decimal("75000.00"), created_by=user,
    )
    
    service = ArabicReportService()
    params = {"farm_id": farm.id}
    pdf_bytes = service.generate_profitability_pdf(params)
    
    out_path = os.path.join(settings.BASE_DIR, "output_pdf_test.pdf")
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)
    
    print(f"SUCCESS: PDF generated ({len(pdf_bytes)} bytes) at {out_path}")
    sys.exit(0)
    
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
