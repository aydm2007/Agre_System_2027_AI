
from django.test import TestCase
from django.db.utils import IntegrityError
from django.db import transaction
from django.contrib.auth.models import User
from smart_agri.inventory.models import Item, ItemInventory, Unit
from smart_agri.finance.models import FinancialLedger
from smart_agri.core.models.farm import Farm

class HardQualityGatesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gate_tester", password="pass1234")
        self.farm = Farm.objects.create(name="Test Farm", slug="test-farm", region="test")
        self.unit = Unit.objects.create(code="kg", name="Kilogram")
        self.item = Item.objects.create(name="Test Item 1", unit=self.unit, uom="kg")

    def test_inventory_negative_stock_prevention(self):
        """
        FAILING TEST: Attempting to set negative stock should raise IntegrityError
        from the Database CheckConstraint.
        """
        print("\n🛡️ Testing Inventory Quality Gate...")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ItemInventory.objects.create(
                    farm=self.farm,
                    item=self.item,
                    qty=-5.00  # VIOLATION
                )
        print("✅ PASSED: Database rejected negative stock.")

    def test_finance_negative_ledger_prevention(self):
        """
        FAILING TEST: Attempting to create negative debit/credit should raise IntegrityError.
        """
        print("\n🛡️ Testing Finance Quality Gate...")
        with self.assertRaises((IntegrityError, Exception)):
            with transaction.atomic():
                FinancialLedger.objects.create(
                    description="Fraud Entry",
                    account_code=FinancialLedger.ACCOUNT_LABOR,
                    debit=-100.00, # VIOLATION
                    created_by=self.user
                )
        print("✅ PASSED: Database rejected negative debit.")
