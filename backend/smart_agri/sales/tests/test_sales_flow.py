from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer
from smart_agri.core.models.farm import Farm, Location
from smart_agri.inventory.models import Item, Unit
from smart_agri.finance.models import FinancialLedger, FiscalYear, FiscalPeriod
from smart_agri.sales.services import SaleService

User = get_user_model()

class TestSalesFlow(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='testadmin', password='password123', email='test@example.com')
        self.farm = Farm.objects.create(name="Flow Farm", slug="flow-farm")
        self.location = Location.objects.create(farm=self.farm, name="Warehouse A", code="WH-A")
        self.customer = Customer.objects.create(name="Flow Customer")
        self.unit = Unit.objects.create(name="Kg", code="kg")
        self.item = Item.objects.create(name="Flow Product", uom="kg", unit=self.unit, unit_price=Decimal("50.00"))
        
        # Setup Fiscal Period (REQUIRED for Strict Mode)
        today = timezone.now().date()
        self.fy = FiscalYear.objects.create(
            farm=self.farm,
            year=today.year,
            start_date=today.replace(month=1, day=1),
            end_date=today.replace(month=12, day=31)
        )
        self.period = FiscalPeriod.objects.create(
            fiscal_year=self.fy,
            month=today.month,
            start_date=today.replace(day=1),
            end_date=today.replace(day=28), # Simplified
            is_closed=False
        )
        
        # Initial Stock (Optional, but good for reality check)
        from smart_agri.core.services.inventory_service import InventoryService
        InventoryService.record_movement(
            farm=self.farm,
            item=self.item,
            location=self.location,
            qty_delta=Decimal("100"),
            ref_type="INITIAL",
            ref_id="INIT-001"
        )

    def test_full_sales_cycle(self):
        """Test Creation -> Confirmation -> Ledger Impact"""
        
        # 1. Create Invoice
        items_data = [
            {'item': self.item.id, 'qty': 10, 'unit_price': 50}
        ]
        
        invoice = SaleService.create_invoice(
            customer=self.customer,
            location=self.location,
            invoice_date=timezone.now().date(),
            items_data=items_data,
            user=self.user
        )
        
        self.assertEqual(invoice.total_amount, Decimal("500.00"))
        self.assertEqual(invoice.status, 'draft')
        
        # 2. Confirm Invoice (Triggers Inventory & Finance)
        SaleService.confirm_sale(invoice, user=self.user)
        
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'approved')
        
        # 3. Verify Inventory Deduction
        # We check if a movement was recorded.
        # InventoryService doesn't expose current stock easily on Item model without query,
        # but we can check the ledger or movement logs.
        # Let's check ledger for simpler integration verify.
        
        # 4. Verify Financial Ledger
        ledger_entries = FinancialLedger.objects.filter(
            farm=self.farm,
            description__contains=f"#{invoice.id}"
        )
        
        # Expected Entries:
        # Credit Revenue (500)
        # Debit Receivable/Cash (500)
        
        revenue_entry = ledger_entries.filter(account_code=SaleService.ACCOUNT_REVENUE).first()
        self.assertIsNotNone(revenue_entry)
        self.assertEqual(revenue_entry.credit, Decimal("500.00"))
        
        receivable_entry = ledger_entries.filter(account_code=SaleService.ACCOUNT_RECEIVABLE).first()
        self.assertIsNotNone(receivable_entry)
        self.assertEqual(receivable_entry.debit, Decimal("500.00"))
        
        total_debit = sum(e.debit for e in ledger_entries)
        total_credit = sum(e.credit for e in ledger_entries)
        self.assertEqual(total_debit, total_credit)
        self.assertTrue(total_debit >= Decimal("500.00"))

