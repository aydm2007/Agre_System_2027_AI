import calendar
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from smart_agri.core.models import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import CostCenter, FinancialLedger, FiscalPeriod, FiscalYear
from smart_agri.finance.models_petty_cash import PettyCashLine, PettyCashRequest, PettyCashSettlement
from smart_agri.finance.models_treasury import CashBox, TreasuryTransaction
from smart_agri.finance.services.petty_cash_service import PettyCashService


class PettyCashServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        suffix = uuid4().hex[:8]
        self.user = user_model.objects.create_superuser(
            username=f"petty-{suffix}",
            email=f"{suffix}@example.com",
            password="pass1234",
        )
        self.requester = user_model.objects.create_user(
            username=f"requester-{suffix}",
            password="pass1234",
        )
        self.farm = Farm.objects.create(name=f"Petty Farm {suffix}", slug=f"petty-farm-{suffix}", region="R1")
        FarmSettings.objects.create(
            farm=self.farm,
            mode=FarmSettings.MODE_STRICT,
            enable_petty_cash=True,
        )
        self.cost_center = CostCenter.objects.create(farm=self.farm, code=f"CC-{suffix}", name="Petty Cash CC")
        self.cash_box = CashBox.objects.create(
            farm=self.farm,
            name="Main Safe",
            box_type=CashBox.MASTER_SAFE,
            currency="YER",
            balance=Decimal("1000.0000"),
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

    def _create_approved_request(self, amount=Decimal("100.0000")):
        return PettyCashRequest.objects.create(
            farm=self.farm,
            requester=self.requester,
            amount=amount,
            description="Field petty cash",
            cost_center=self.cost_center,
            status=PettyCashRequest.STATUS_APPROVED,
            approved_by=self.user,
        )

    def test_disburse_request_posts_cash_and_suspense_entries(self):
        request_obj = self._create_approved_request()

        result = PettyCashService.disburse_request(request_obj.id, self.cash_box.id, self.user)

        self.assertEqual(result.status, PettyCashRequest.STATUS_DISBURSED)
        self.cash_box.refresh_from_db()
        self.assertEqual(self.cash_box.balance, Decimal("900.0000"))
        self.assertEqual(TreasuryTransaction.objects.filter(farm=self.farm).count(), 1)
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
                credit=Decimal("100.0000"),
                description=f"Issue Petty Cash #{request_obj.id}",
            ).exists()
        )
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_SUSPENSE,
                debit=Decimal("100.0000"),
                description=f"Custody for Petty Cash #{request_obj.id}",
            ).exists()
        )

    def test_settle_request_clears_suspense_and_books_refund(self):
        request_obj = self._create_approved_request()
        PettyCashService.disburse_request(request_obj.id, self.cash_box.id, self.user)

        settlement = PettyCashSettlement.objects.create(
            request=request_obj,
            total_expenses=Decimal("0.0000"),
            refund_amount=Decimal("0.0000"),
        )
        PettyCashLine.objects.create(
            settlement=settlement,
            amount=Decimal("70.0000"),
            description="Fuel receipt",
        )

        from smart_agri.core.models.log import Attachment
        Attachment.objects.create(
            farm=self.farm,
            file=SimpleUploadedFile(
                "dummy.pdf",
                b"%PDF-1.4 petty cash settlement attachment",
                content_type="application/pdf",
            ),
            uploaded_by=self.user,
            filename_original="dummy.pdf",
            related_document_type="petty_cash_settlement",
            document_scope=str(settlement.id),
            malware_scan_status=Attachment.MALWARE_SCAN_PASSED,
        )

        result = PettyCashService.settle_request(settlement.id, self.user)

        self.assertEqual(result.status, PettyCashSettlement.STATUS_APPROVED)
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, PettyCashRequest.STATUS_SETTLED)
        self.cash_box.refresh_from_db()
        self.assertEqual(self.cash_box.balance, Decimal("930.0000"))
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_SUSPENSE,
                credit=Decimal("100.0000"),
                description=f"Clear Custody PC #{request_obj.id}",
            ).exists()
        )
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_EXPENSE_ADMIN,
                debit=Decimal("70.0000"),
                description__startswith="PC Exp:",
            ).exists()
        )
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
                debit=Decimal("30.0000"),
                description=f"Refund PC #{request_obj.id}",
            ).exists()
        )
        self.assertEqual(TreasuryTransaction.objects.filter(farm=self.farm).count(), 2)

    def test_disburse_request_respects_toggle(self):
        settings = self.farm.settings
        settings.enable_petty_cash = False
        settings.save(update_fields=["enable_petty_cash"])
        request_obj = self._create_approved_request()

        with self.assertRaises(ValidationError):
            PettyCashService.disburse_request(request_obj.id, self.cash_box.id, self.user)

    def test_settle_labor_liability_clears_payable(self):
        """[Axis 17] Labor settlement should clear salaries payable."""
        from smart_agri.core.models import DailyLog
        log = DailyLog.objects.create(farm=self.farm, log_date=timezone.localdate(), status='approved')
        
        request_obj = self._create_approved_request(amount=Decimal("300.0000"))
        PettyCashService.disburse_request(request_obj.id, self.cash_box.id, self.user)

        settlement = PettyCashSettlement.objects.create(
            request=request_obj,
            total_expenses=Decimal("0.0000"),
            refund_amount=Decimal("0.0000"),
        )
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        from smart_agri.core.models.log import Attachment
        Attachment.objects.create(
            farm=self.farm,
            file=SimpleUploadedFile(
                "labor_receipt.pdf",
                b"%PDF-1.4 labor payment evidence",
                content_type="application/pdf",
            ),
            uploaded_by=self.user,
            filename_original="labor_receipt.pdf",
            related_document_type="petty_cash_settlement",
            document_scope=str(settlement.id),
            malware_scan_status=Attachment.MALWARE_SCAN_PASSED,
        )

        line = PettyCashLine.objects.create(
            settlement=settlement,
            amount=Decimal("200.0000"),
            description="Labor workers payment",
            is_labor_settlement=True,
            related_daily_log=log
        )

        result = PettyCashService.settle_request(settlement.id, self.user)

        self.assertEqual(result.status, PettyCashSettlement.STATUS_APPROVED)
        # Verify it debited ACCOUNT_PAYABLE_SALARIES (1620)
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
                debit=Decimal("200.0000")
            ).exists()
        )
        # Verify standard expense was NOT created for this line
        self.assertFalse(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_EXPENSE_ADMIN,
                debit=Decimal("200.0000")
            ).exists()
        )
