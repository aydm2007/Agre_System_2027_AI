from decimal import Decimal

from django.test import TestCase

from smart_agri.core.models import Asset, Farm
from smart_agri.core.services.asset_service import AssetService
from smart_agri.core.services.harvest_service import HarvestService


class Phase6ZakatSolarTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Phase6 Farm", slug="phase6-farm", region="north")

    def test_zakat_rate_5_percent(self):
        result = HarvestService.calculate_zakat_due(Decimal("1000"), Farm.ZAKAT_HALF_TITHE)
        self.assertEqual(result, Decimal("50.0000"))

    def test_zakat_rate_10_percent(self):
        result = HarvestService.calculate_zakat_due(Decimal("1000"), Farm.ZAKAT_TITHE)
        self.assertEqual(result, Decimal("100.0000"))

    def test_solar_operational_depreciation_per_hour(self):
        asset = Asset.objects.create(
            farm=self.farm,
            category="Solar",
            name="Solar Pump Array",
            purchase_value=Decimal("24000.00"),
            salvage_value=Decimal("0.00"),
            useful_life_years=10,
        )
        dep = AssetService.calculate_operational_solar_depreciation(asset, Decimal("24"))
        # 24000 / (10*365*24) = 0.2739726... per hour; 6dp hourly rate then 4dp total.
        self.assertEqual(dep, Decimal("6.5754"))
