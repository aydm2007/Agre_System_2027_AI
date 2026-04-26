import os
import sys
from decimal import Decimal

# Setup Django Environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
import django
django.setup()

from django.test import TestCase
from django.conf import settings
from smart_agri.core.services.reporting_service import ArabicReportService
from smart_agri.finance.models import FinancialLedger
from smart_agri.core.models.farm import Farm
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger('test_pdf')

class PDFGenerationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="pdf_tester")
        self.farm = Farm.objects.create(name="مزرعة تجريبية", code="TEST-01")
        
        # Create some ledger records
        # Revenue
        FinancialLedger.objects.create(
            farm=self.farm,
            account_code="4000-REV",
            description="مبيعات محصول",
            credit=Decimal("150000.00"),
            debit=Decimal("0.00"),
            created_by=self.user,
        )
        
        # Expense
        FinancialLedger.objects.create(
            farm=self.farm,
            account_code="7000-EXP",
            description="مصروفات تشغيلية",
            credit=Decimal("0.00"),
            debit=Decimal("50000.00"),
            created_by=self.user,
        )
        
    def test_pdf_creation(self):
        service = ArabicReportService()
        params = {"farm_id": self.farm.id}
        
        pdf_bytes = service.generate_profitability_pdf(params)
        
        self.assertIsNotNone(pdf_bytes)
        self.assertGreater(len(pdf_bytes), 1000) # Ensure it has content
        
        # write out to file for manual visual inspection
        out_path = os.path.join(settings.BASE_DIR, "test_output.pdf")
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
            
        print(f"[OK] PDF Successfully generated to {out_path} ({len(pdf_bytes)} bytes)")
        
if __name__ == '__main__':
    import unittest
    unittest.main()
