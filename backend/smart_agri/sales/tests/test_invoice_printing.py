from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer
from smart_agri.core.models.farm import Farm
from smart_agri.inventory.models import Item, Unit

User = get_user_model()

class TestInvoicePrinting(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(username='testadmin', password='password123', email='test@example.com')
        self.client.force_authenticate(user=self.user)
        
        # Setup basic data
        self.farm = Farm.objects.create(name="Test Farm", slug="test-farm")
        self.customer = Customer.objects.create(name="Test Customer", phone="123456789")
        self.unit = Unit.objects.create(name="Kg", code="kg")
        self.item = Item.objects.create(name="Test Mango", uom="kg", unit=self.unit, unit_price=Decimal("100"))
        
        # Create Invoice
        self.invoice = SalesInvoice.objects.create(
            farm=self.farm,
            customer=self.customer,
            invoice_date=timezone.now().date(),
            status='approved',
            created_by=self.user,
            total_amount=Decimal("500")
        )
        
        SalesInvoiceItem.objects.create(
            invoice=self.invoice,
            item=self.item,
            qty=Decimal("5"),
            unit_price=Decimal("100"),
            total=Decimal("500")
        )

    def test_get_invoice_details_for_print(self):
        """Test retrieving invoice details including items for printing"""
        response = self.client.get(f'/api/v1/sales-invoices/{self.invoice.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify Key Print-Required Fields
        self.assertEqual(response.data['invoice_number'], self.invoice.invoice_number)
        self.assertEqual(response.data['customer_name'], "Test Customer")
        self.assertEqual(response.data['farm_name'], "Test Farm")
        self.assertEqual(Decimal(str(response.data['total_amount'])), Decimal('500.00'))
        
        # Verify Items
        items = response.data.get('items', [])
        self.assertTrue(len(items) > 0)
        self.assertEqual(items[0]['product_name'], "Test Mango")
        self.assertEqual(Decimal(str(items[0]['qty'])), Decimal('5.00'))
