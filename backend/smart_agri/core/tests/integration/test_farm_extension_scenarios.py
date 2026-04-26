from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from smart_agri.core.models.farm import Farm, Location, Asset, LocationWell
from smart_agri.core.models.crop import Crop, CropVariety
from smart_agri.inventory.models import Item, Unit
from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer
from smart_agri.finance.models import FiscalYear, FiscalPeriod

User = get_user_model()

class TestFarmExtensionScenarios(TestCase):
    """
    [Agri-Guardian] Comprehensive Verification of Farm Extension Scenarios.
    Covers:
    A. Expanding Crops & Varieties (Best Practices)
    B. Adding Machinery & Wells
    C. Linking Wells to Locations
    D. Sales Flow Integration
    """

    def setUp(self):
        self.user = User.objects.create_superuser(username='farmadmin', password='password123', email='admin@example.com')
        self.farm = Farm.objects.create(name="Al Mahmadieh Test", slug="al-mahmadieh-test")
        
        # Setup Fiscal Year for transactions
        today = timezone.now().date()
        self.fy = FiscalYear.objects.create(
            farm=self.farm, 
            year=today.year, 
            start_date=today.replace(month=1, day=1), 
            end_date=today.replace(month=12, day=31)
        )
        self.period = FiscalPeriod.objects.create(
            fiscal_year=self.fy, month=today.month, 
            start_date=today.replace(day=1), end_date=today.replace(day=28), is_closed=False
        )

    def test_scenario_a_add_crops_and_varieties(self):
        """Verify adding crops/varieties adheres to integrity rules."""
        # 1. Add Crop (Wheat)
        wheat = Crop.objects.create(name="Wheat Test", is_perennial=False, mode="Open")
        
        # 2. Add Variety (Local)
        variety = CropVariety.objects.create(crop=wheat, name="Local Wheat", code="WHEAT-LOC-01", est_days_to_harvest=120)
        
        # Verify
        self.assertEqual(variety.crop.name, "Wheat Test")
        self.assertEqual(variety.code, "WHEAT-LOC-01")
        self.assertTrue(variety.est_days_to_harvest > 0)

    def test_scenario_b_machinery_and_wells(self):
        """Verify adding assets (Wells/Machinery) with correct categories."""
        # 1. Add Well
        well = Asset.objects.create(
            farm=self.farm,
            name="Main Well Test",
            category="Well",
            code="WELL-TEST-01",
            purchase_value=Decimal("500000")
        )
        
        # 2. Add Machinery
        tractor = Asset.objects.create(
            farm=self.farm,
            name="Tractor Test",
            category="Machinery", 
            code="TRAC-TEST-01",
            purchase_value=Decimal("800000")
        )
        
        # Verify
        self.assertEqual(well.category, "Well")
        self.assertEqual(tractor.category, "Machinery")
        self.assertEqual(well.purchase_value, Decimal("500000"))

    def test_scenario_c_linking_wells_to_locations(self):
        """Verify linking a well to a specific location."""
        # 1. Create Location & Well
        field = Location.objects.create(farm=self.farm, name="North Field", code="FLD-N")
        well = Asset.objects.create(farm=self.farm, name="Well 1", category="Well", code="W1")
        
        # 2. Link
        link = LocationWell.objects.create(
            location=field,
            asset=well,
            well_depth=Decimal("100"),
            capacity_lps=Decimal("15")
        )
        
        # Verify
        self.assertEqual(link.location.name, "North Field")
        self.assertEqual(link.asset.name, "Well 1")
        self.assertTrue(link.is_operational)

    def test_scenario_d_sales_integration(self):
        """Verify sales invoice creation linked to Farm/Location."""
        # 1. Setup Data
        customer = Customer.objects.create(name="Test Customer")
        field = Location.objects.create(farm=self.farm, name="North Field", code="FLD-N")
        unit = Unit.objects.create(name="Kg", code="kg")
        mango = Item.objects.create(name="Mango Test", uom="kg", unit=unit, unit_price=Decimal("20"))
        
        # 2. Create Invoice
        invoice = SalesInvoice.objects.create(
            farm=self.farm,
            customer=customer,
            location=field, # Linking to source location (Best Practice)
            invoice_date=timezone.now().date(),
            total_amount=Decimal("2000"),
            created_by=self.user
        )
        
        # 3. Add Item
        SalesInvoiceItem.objects.create(
            invoice=invoice,
            item=mango,
            qty=Decimal("100"),
            unit_price=Decimal("20"),
            total=Decimal("2000")
        )
        
        # Verify
        self.assertEqual(invoice.total_amount, Decimal("2000"))
        self.assertEqual(invoice.location.code, "FLD-N")
