import calendar
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from smart_agri.core.models import AuditLog, Crop, Farm, Location
from smart_agri.core.models.partnerships import (
    IrrigationType,
    SharecroppingContract,
    SharecroppingReceipt,
    TouringAssessment,
)
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.sharecropping_posting_service import SharecroppingPostingService
from smart_agri.finance.models import FinancialLedger, FiscalPeriod, FiscalYear
from smart_agri.inventory.models import Item, ItemInventory, StockMovement


class SharecroppingPostingServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        suffix = uuid4().hex[:8]
        self.user = user_model.objects.create_superuser(
            username=f"sharecrop-{suffix}",
            email=f"{suffix}@example.com",
            password="pass1234",
        )
        self.farm = Farm.objects.create(name=f"Share Farm {suffix}", slug=f"share-farm-{suffix}", region="R1")
        self.crop = Crop.objects.create(name=f"Crop {suffix}", mode="Open")
        self.location = Location.objects.create(farm=self.farm, name=f"Location {suffix}")
        FarmSettings.objects.create(
            farm=self.farm,
            mode=FarmSettings.MODE_STRICT,
            enable_sharecropping=True,
            sharecropping_mode=FarmSettings.SHARECROPPING_MODE_FINANCIAL,
        )

        today = timezone.localdate()
        fiscal_year = FiscalYear.objects.create(
            farm=self.farm,
            year=today.year,
            start_date=today.replace(month=1, day=1),
            end_date=today.replace(month=12, day=31),
        )
        FiscalPeriod.objects.create(
            fiscal_year=fiscal_year,
            month=today.month,
            start_date=today.replace(day=1),
            end_date=today.replace(day=calendar.monthrange(today.year, today.month)[1]),
            status=FiscalPeriod.STATUS_OPEN,
            is_closed=False,
        )

    def _create_assessment(self):
        contract = SharecroppingContract.objects.create(
            farm=self.farm,
            farmer_name="Partner Farmer",
            crop=self.crop,
            irrigation_type=IrrigationType.WELL_PUMP,
            institution_percentage=Decimal("0.3000"),
        )
        return TouringAssessment.objects.create(
            contract=contract,
            estimated_total_yield_kg=Decimal("1000.0000"),
            expected_zakat_kg=Decimal("50.0000"),
            expected_institution_share_kg=Decimal("300.0000"),
            committee_members=["A", "B", "C"],
        )

    def test_financial_mode_posts_cash_and_revenue(self):
        assessment = self._create_assessment()
        receipt = SharecroppingReceipt.objects.create(
            farm=self.farm,
            assessment=assessment,
            receipt_type=SharecroppingReceipt.RECEIPT_TYPE_FINANCIAL,
            amount_received=Decimal("125.5000"),
            received_by=self.user,
        )

        result = SharecroppingPostingService.post_receipt(receipt_id=receipt.id, user=self.user)

        self.assertEqual(result["status"], "posted")
        self.assertEqual(result["posting_mode"], FarmSettings.SHARECROPPING_MODE_FINANCIAL)
        receipt.refresh_from_db()
        self.assertTrue(receipt.is_posted)
        self.assertEqual(
            FinancialLedger.objects.filter(farm=self.farm, description__contains=f"#{receipt.id}").count(),
            2,
        )
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
                debit=Decimal("125.5000"),
                description__contains=f"#{receipt.id}",
            ).exists()
        )
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_SALES_REVENUE,
                credit=Decimal("125.5000"),
                description__contains=f"#{receipt.id}",
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="SHARECROPPING_RECEIPT_POSTED",
                model="SharecroppingReceipt",
                object_id=str(receipt.id),
            ).exists()
        )

    def test_post_receipt_is_idempotent_after_first_post(self):
        assessment = self._create_assessment()
        receipt = SharecroppingReceipt.objects.create(
            farm=self.farm,
            assessment=assessment,
            receipt_type=SharecroppingReceipt.RECEIPT_TYPE_FINANCIAL,
            amount_received=Decimal("50.0000"),
            received_by=self.user,
        )

        first = SharecroppingPostingService.post_receipt(receipt_id=receipt.id, user=self.user)
        second = SharecroppingPostingService.post_receipt(receipt_id=receipt.id, user=self.user)

        self.assertEqual(first["status"], "posted")
        self.assertEqual(second["status"], "already_posted")
        self.assertEqual(
            FinancialLedger.objects.filter(farm=self.farm, description__contains=f"#{receipt.id}").count(),
            2,
        )

    def test_physical_mode_posts_inventory_and_stock_movement(self):
        settings = self.farm.settings
        settings.sharecropping_mode = FarmSettings.SHARECROPPING_MODE_PHYSICAL
        settings.save(update_fields=["sharecropping_mode"])

        assessment = self._create_assessment()
        item = Item.objects.create(
            name=f"Produce {uuid4().hex[:6]}",
            group="Produce",
            uom="kg",
            unit_price=Decimal("2.000"),
        )
        inventory = ItemInventory.objects.create(
            farm=self.farm,
            location=self.location,
            item=item,
            qty=Decimal("0.000"),
            uom="kg",
        )
        receipt = SharecroppingReceipt.objects.create(
            farm=self.farm,
            assessment=assessment,
            receipt_type=SharecroppingReceipt.RECEIPT_TYPE_PHYSICAL,
            quantity_received_kg=Decimal("200.0000"),
            destination_inventory=inventory,
            received_by=self.user,
        )

        result = SharecroppingPostingService.post_receipt(receipt_id=receipt.id, user=self.user)

        self.assertEqual(result["status"], "posted")
        self.assertEqual(result["posting_mode"], FarmSettings.SHARECROPPING_MODE_PHYSICAL)
        self.assertEqual(result["estimated_value"], "400.0000")
        inventory.refresh_from_db()
        self.assertEqual(inventory.qty, Decimal("200.000"))
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_INVENTORY_ASSET,
                debit=Decimal("400.0000"),
                description__contains=f"#{receipt.id}",
            ).exists()
        )
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_SALES_REVENUE,
                credit=Decimal("400.0000"),
                description__contains=f"#{receipt.id}",
            ).exists()
        )
        self.assertTrue(
            StockMovement.objects.filter(
                farm=self.farm,
                item=item,
                location=self.location,
                ref_type="sharecropping_receipt",
                ref_id=str(receipt.id),
            ).exists()
        )
