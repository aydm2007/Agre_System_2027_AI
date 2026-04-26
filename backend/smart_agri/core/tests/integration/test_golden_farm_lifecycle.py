from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm, Location
from smart_agri.core.models.crop import Crop
from smart_agri.core.models.planning import CropPlan
from smart_agri.finance.models import FinancialLedger, FiscalPeriod, FiscalYear
from smart_agri.inventory.models import Item, ItemInventory
from smart_agri.sales.models import Customer
from smart_agri.sales.services import SaleService


class GoldenFarmFullCycleTest(TestCase):
    """
    Integration coverage for the Golden farm lifecycle in current schema:
    - Farm tier auto-classification
    - Fiscal period state-machine
    - Idempotent sales confirmation with ledger stability
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("golden-manager", password="pass123")
        cls.approver = User.objects.create_user("golden-approver", password="pass123")

        cls.farm = Farm.objects.create(
            name="مزرعة القولدن",
            slug="golden-farm",
            region="North",
            area=Decimal("120"),
        )
        FarmMembership.objects.create(user=cls.user, farm=cls.farm, role="Manager")
        FarmMembership.objects.create(user=cls.approver, farm=cls.farm, role="Manager")

        cls.location = Location.objects.create(farm=cls.farm, name="القطاع الأول")
        cls.crop = Crop.objects.create(name="مانجو")
        cls.plan = CropPlan.objects.create(
            farm=cls.farm,
            crop=cls.crop,
            location=cls.location,
            name="خطة 2026",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            budget_materials=Decimal("500000.0000"),
            budget_labor=Decimal("300000.0000"),
            budget_machinery=Decimal("100000.0000"),
            created_by=cls.user,
        )

        cls.item_mango = Item.objects.create(
            name="مانجو درجة أولى",
            group="Produce",
            uom='kg',
            unit_price=Decimal("800.000"),
        )
        ItemInventory.objects.create(
            farm=cls.farm,
            location=cls.location,
            item=cls.item_mango,
            qty=Decimal("600.000"),
            uom='kg',
        )
        cls.customer = Customer.objects.create(name="تاجر الفواكه")

        cls.fiscal_year = FiscalYear.objects.create(
            farm=cls.farm,
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_closed=False,
        )
        cls.fiscal_period = FiscalPeriod.objects.create(
            fiscal_year=cls.fiscal_year,
            month=2,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            status=FiscalPeriod.STATUS_OPEN,
        )

    def test_01_tier_auto_classification(self):
        self.farm.refresh_from_db()
        self.assertEqual(self.farm.tier, Farm.TIER_MEDIUM)

        small = Farm.objects.create(
            name="مزرعة صغيرة",
            slug="small-farm",
            region="North",
            area=Decimal("20"),
        )
        self.assertEqual(small.tier, Farm.TIER_SMALL)

    def test_02_fiscal_state_machine_open_soft_hard(self):
        period = self.fiscal_period
        self.assertEqual(period.status, FiscalPeriod.STATUS_OPEN)

        period.status = FiscalPeriod.STATUS_SOFT_CLOSE
        period.save()
        period.refresh_from_db()
        self.assertEqual(period.status, FiscalPeriod.STATUS_SOFT_CLOSE)

        period.status = FiscalPeriod.STATUS_HARD_CLOSE
        period.save()
        period.refresh_from_db()
        self.assertEqual(period.status, FiscalPeriod.STATUS_HARD_CLOSE)

    def test_03_sales_confirm_is_idempotent(self):
        invoice = SaleService.create_invoice(
            customer=self.customer,
            location=self.location,
            invoice_date=date(2026, 2, 15),
            items_data=[
                {
                    "item": self.item_mango.id,
                    "qty": "100.000",
                    "unit_price": "1200.00",
                }
            ],
            user=self.user,
            notes="Golden lifecycle confirm",
        )
        self.assertEqual(str(invoice.status), "draft")

        SaleService.confirm_sale(invoice, user=self.approver)
        first_count = FinancialLedger.objects.filter(object_id=str(invoice.id)).count()
        SaleService.confirm_sale(invoice, user=self.approver)
        second_count = FinancialLedger.objects.filter(object_id=str(invoice.id)).count()

        self.assertEqual(first_count, second_count)
        self.assertGreater(first_count, 0)
