import calendar
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.log import Attachment
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import FiscalPeriod, FiscalYear, FinancialLedger
from smart_agri.finance.models_supplier_settlement import SupplierSettlement
from smart_agri.finance.models_treasury import CashBox, TreasuryTransaction
from smart_agri.inventory.models import PurchaseOrder


class SupplierSettlementApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="supplier_finance",
            email="supplier@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(self.user)
        self.reviewer = User.objects.create_user(
            username="supplier_reviewer",
            email="supplier-reviewer@example.com",
            password="pass1234",
        )
        self.final_approver = User.objects.create_user(
            username="supplier_sector_director",
            email="supplier-sector@example.com",
            password="pass1234",
        )
        self.reviewer_client = APIClient()
        self.final_client = APIClient()

        self.farm = Farm.objects.create(name="Supplier Farm", slug="supplier-farm", region="R1")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Admin")
        FarmMembership.objects.create(user=self.reviewer, farm=self.farm, role="المدير المالي للمزرعة")
        FarmMembership.objects.create(user=self.final_approver, farm=self.farm, role="مدير القطاع")
        FarmSettings.objects.create(
            farm=self.farm,
            mode=FarmSettings.MODE_STRICT,
            treasury_visibility=FarmSettings.TREASURY_VISIBILITY_VISIBLE,
            approval_profile=FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE,
        )
        self.client.credentials(HTTP_X_FARM_ID=str(self.farm.id))
        self.reviewer_client.force_authenticate(self.reviewer)
        self.reviewer_client.credentials(HTTP_X_FARM_ID=str(self.farm.id))
        self.final_client.force_authenticate(self.final_approver)
        self.final_client.credentials(HTTP_X_FARM_ID=str(self.farm.id))
        self.cashbox = CashBox.objects.create(
            farm=self.farm,
            name="Supplier Safe",
            box_type=CashBox.MASTER_SAFE,
            currency="YER",
            balance=Decimal("5000.0000"),
        )
        today = timezone.localdate()
        fy = FiscalYear.objects.create(
            farm=self.farm,
            year=today.year,
            start_date=today.replace(month=1, day=1),
            end_date=today.replace(month=12, day=31),
            is_closed=False,
        )
        FiscalPeriod.objects.create(
            fiscal_year=fy,
            month=today.month,
            start_date=today.replace(day=1),
            end_date=today.replace(day=calendar.monthrange(today.year, today.month)[1]),
            status=FiscalPeriod.STATUS_OPEN,
            is_closed=False,
        )
        self.purchase_order = PurchaseOrder.objects.create(
            farm=self.farm,
            vendor_name="Green Supplier",
            status=PurchaseOrder.Status.APPROVED,
            total_amount=Decimal("1200.0000"),
            currency="YER",
        )

    def test_supplier_settlement_lifecycle_supports_partial_and_full_payment(self):
        create_resp = self.client.post(
            "/api/v1/finance/supplier-settlements/",
            {
                "purchase_order": self.purchase_order.id,
                "invoice_reference": "INV-001",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="supplier-create-1",
        )
        self.assertEqual(create_resp.status_code, 201)
        settlement_id = create_resp.json()["id"]

        submit_resp = self.reviewer_client.post(
            f"/api/v1/finance/supplier-settlements/{settlement_id}/submit_review/",
            {},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="supplier-submit-1",
        )
        self.assertEqual(submit_resp.status_code, 200)
        self.assertEqual(submit_resp.json()["status"], SupplierSettlement.STATUS_UNDER_REVIEW)

        Attachment.objects.create(
            farm=self.farm,
            file=SimpleUploadedFile(
                "supplier-attachment.pdf",
                b"%PDF-1.4 supplier settlement attachment",
                content_type="application/pdf",
            ),
            uploaded_by=self.final_approver,
            filename_original="supplier-attachment.pdf",
            related_document_type="supplier_settlement",
            document_scope=str(settlement_id),
            malware_scan_status=Attachment.MALWARE_SCAN_PASSED,
        )

        approve_resp = self.final_client.post(
            f"/api/v1/finance/supplier-settlements/{settlement_id}/approve/",
            {},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="supplier-approve-1",
        )
        self.assertEqual(approve_resp.status_code, 200)
        self.assertEqual(approve_resp.json()["status"], SupplierSettlement.STATUS_APPROVED)

        partial_resp = self.client.post(
            f"/api/v1/finance/supplier-settlements/{settlement_id}/record_payment/",
            {
                "cash_box_id": self.cashbox.id,
                "amount": "500.0000",
                "reference": "PAY-001",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="supplier-pay-1",
        )
        self.assertEqual(partial_resp.status_code, 200)
        self.assertEqual(partial_resp.json()["status"], SupplierSettlement.STATUS_PARTIALLY_PAID)
        self.assertEqual(partial_resp.json()["reconciliation_state"], "PARTIAL")
        self.assertEqual(partial_resp.json()["variance_severity"], "warning")

        paid_resp = self.client.post(
            f"/api/v1/finance/supplier-settlements/{settlement_id}/record_payment/",
            {
                "cash_box_id": self.cashbox.id,
                "amount": "700.0000",
                "reference": "PAY-002",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="supplier-pay-2",
        )
        self.assertEqual(paid_resp.status_code, 200)
        self.assertEqual(paid_resp.json()["status"], SupplierSettlement.STATUS_PAID)
        self.assertEqual(paid_resp.json()["reconciliation_state"], "MATCHED")
        self.assertEqual(len(paid_resp.json()["payments"]), 2)

        self.cashbox.refresh_from_db()
        self.assertEqual(self.cashbox.balance, Decimal("3800.0000"))
        self.assertEqual(TreasuryTransaction.objects.filter(farm=self.farm).count(), 2)
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                account_code=FinancialLedger.ACCOUNT_PAYABLE_VENDOR,
            ).exists()
        )

    def test_record_payment_rejects_invalid_payable_source(self):
        settlement = SupplierSettlement.objects.create(
            farm=self.farm,
            purchase_order=self.purchase_order,
            invoice_reference="INV-002",
            due_date=timezone.localdate(),
            payable_amount=Decimal("1200.0000"),
            status=SupplierSettlement.STATUS_APPROVED,
            created_by=self.user,
        )
        self.purchase_order.status = PurchaseOrder.Status.DRAFT
        self.purchase_order.save(update_fields=["status"])

        resp = self.client.post(
            f"/api/v1/finance/supplier-settlements/{settlement.id}/record_payment/",
            {
                "cash_box_id": self.cashbox.id,
                "amount": "100.0000",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="supplier-invalid-pay-1",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("valid approved payable source", str(resp.json()))

    def test_list_exposes_policy_snapshot_and_cost_display_mode(self):
        settlement = SupplierSettlement.objects.create(
            farm=self.farm,
            purchase_order=self.purchase_order,
            invoice_reference="INV-003",
            due_date=timezone.localdate(),
            payable_amount=Decimal("1200.0000"),
            status=SupplierSettlement.STATUS_DRAFT,
            created_by=self.user,
        )
        resp = self.client.get(f"/api/v1/finance/supplier-settlements/?farm_id={self.farm.id}")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        row = payload["results"][0] if isinstance(payload, dict) and "results" in payload else payload[0]
        self.assertEqual(row["id"], settlement.id)
        self.assertEqual(row["cost_display_mode"], "summarized_amounts")
        self.assertEqual(row["visibility_level"], "full_erp")
        self.assertEqual(row["policy_snapshot"]["mode"], "STRICT")

    def test_supplier_settlement_idempotency(self):
        """[M4.4] Validates that repeated idempotent requests return the original payload without double ledger processing."""
        resp1 = self.client.post(
            "/api/v1/finance/supplier-settlements/",
            {
                "purchase_order": self.purchase_order.id,
                "invoice_reference": "INV-IDEMP",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="supplier-idemp-key",
        )
        self.assertEqual(resp1.status_code, 201)
        
        count_before_replay = SupplierSettlement.objects.count()
        
        resp2 = self.client.post(
            "/api/v1/finance/supplier-settlements/",
            {
                "purchase_order": self.purchase_order.id,
                "invoice_reference": "INV-IDEMP",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="supplier-idemp-key",
        )
        # Should return 200 or 201 with identical ID but not create a new one
        self.assertEqual(SupplierSettlement.objects.count(), count_before_replay)
        self.assertEqual(resp1.json()["id"], resp2.json()["id"])

