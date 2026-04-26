from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from smart_agri.core.models import Asset, FinancialLedger, Farm
from smart_agri.core.services.asset_service import AssetService

class AssetDepreciationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cfo')
        self.farm = Farm.objects.create(name="Tech Farm", total_area=100)
        
        # Create Asset
        # Value: 60,000. Life: 5 Years. Salvage: 0.
        # Monthly Dep = 60,000 / (5*12) = 1,000.
        self.tractor = Asset.objects.create(
            farm=self.farm,
            category="Machinery",
            name="John Deere Tractor",
            purchase_value=Decimal("60000.00"),
            salvage_value=Decimal("0.00"),
            useful_life_years=5,
            depreciation_method=Asset.METHOD_STRAIGHT_LINE
        )

    def test_monthly_depreciation_run(self):
        """Test that run_monthly_depreciation calculates correctly and books to GL."""
        
        # Run 1st Month
        count = AssetService.run_monthly_depreciation(self.user)
        self.assertEqual(count, 1)
        
        self.tractor.refresh_from_db()
        expected_dep = Decimal("1000.00")
        self.assertEqual(self.tractor.accumulated_depreciation, expected_dep)
        
        # Check Ledger
        expense = FinancialLedger.objects.filter(
            account_code=FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
            description__contains="John Deere"
        ).first()
        
        self.assertIsNotNone(expense)
        self.assertEqual(expense.debit, expected_dep)
        
        # Run 2nd Month
        count2 = AssetService.run_monthly_depreciation(self.user)
        
        self.tractor.refresh_from_db()
        self.assertEqual(self.tractor.accumulated_depreciation, expected_dep * 2)

    def test_salvage_value_cap(self):
        """Test that depreciation stops at salvage value."""
        # Value: 1000. Salvage: 900. Life: 1 year.
        # Depreciable Amount: 100.
        # Monthly: 100 / 12 = 8.33
        
        small_asset = Asset.objects.create(
             farm=self.farm, category="Solar", name="Small Panel",
             purchase_value=Decimal("1000.00"),
             salvage_value=Decimal("900.00"),
             useful_life_years=10, # Very slow to test loop, so let's pre-fill
             depreciation_method=Asset.METHOD_STRAIGHT_LINE
        )
        
        # Manually jump to near end
        small_asset.accumulated_depreciation = Decimal("95.00") # Limit is 100. Gap is 5.
        small_asset.save()
        
        # Run logic. Standard calculation might give > 5. (e.g. 100/120 = 0.83).
        # Let's use a simpler case: limit 100. Current 90. Monthly calced = 20. Should cap at 10.
        
        small_asset.useful_life_years = 1 
        small_asset.save()
        # Monthly = 100 / 12 = 8.33.
        # Remaining room = 100 - 95 = 5.00
        # Should book 5.00
        
        AssetService.run_monthly_depreciation(self.user)
        small_asset.refresh_from_db()
        
        self.assertEqual(small_asset.accumulated_depreciation, Decimal("100.00")) # 95 + 5
