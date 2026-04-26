import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.crop import Crop
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.log import Attachment, AuditLog, DailyLog
from smart_agri.core.models.planning import CropPlan
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import ApprovalRequest, ApprovalRule
from smart_agri.finance.models_supplier_settlement import SupplierSettlement
from smart_agri.finance.services.approval_service import ApprovalGovernanceService
from smart_agri.finance.services.supplier_settlement_service import SupplierSettlementService
from smart_agri.inventory.models import PurchaseOrder

User = get_user_model()
logger = logging.getLogger(__name__)


class V21E2ECycleSimulation(TestCase):
    """
    [AGRI-GUARDIAN] V21 E2E Cycle Simulation.
    Validates:
      1. Baseline data provisioning (Users, roles).
      2. Farm dual-modalities: SIMPLE vs STRICT setups.
      3. Crops & Activities linked intrinsically to Smart Cards.
      4. Execution of Daily Logs in SIMPLE mode.
      5. Execution of STRICT financial cycle (Supplier Settlement + Maker-Checker Approval).
      6. Verifying Mode Boundaries continuously.
    """

    def setUp(self):
        self.sys_admin = User.objects.create_user(username="sysadmin", password="password")
        self.sys_admin.is_superuser = True
        self.sys_admin.save()

        self.field_op = User.objects.create_user(username="field_op", password="password")
        self.farm_manager = User.objects.create_user(username="farm_mgr", password="password")
        self.finance_mgr = User.objects.create_user(username="finance_mgr", password="password")
        self.sector_accountant = User.objects.create_user(username="sector_acct", password="password")
        self.sector_director = User.objects.create_user(username="sector_dir", password="password")

        self.farm_simple = Farm.objects.create(name="Waha Simple Farm", slug="waha-simple", tier="SMALL")
        FarmSettings.objects.create(farm=self.farm_simple, mode=FarmSettings.MODE_SIMPLE)

        self.farm_strict = Farm.objects.create(name="Jaruba Strict Farm", slug="jaruba-strict", tier="LARGE")
        FarmSettings.objects.create(farm=self.farm_strict, mode=FarmSettings.MODE_STRICT)

        FarmMembership.objects.create(user=self.field_op, farm=self.farm_simple, role="مشرف ميداني")
        FarmMembership.objects.create(user=self.farm_manager, farm=self.farm_simple, role="مشرف ميداني")
        FarmMembership.objects.create(user=self.farm_manager, farm=self.farm_strict, role="مدير النظام")
        FarmMembership.objects.create(user=self.finance_mgr, farm=self.farm_strict, role="المدير المالي للمزرعة")
        FarmMembership.objects.create(user=self.sector_accountant, farm=self.farm_strict, role="محاسب القطاع")
        FarmMembership.objects.create(user=self.sector_director, farm=self.farm_strict, role="مدير القطاع")

        self.crop = Crop.objects.create(name="Tomato Target")
        self.plan = CropPlan.objects.create(
            farm=self.farm_simple,
            crop=self.crop,
            name="Q1 Tomato Smart Card Plan",
        )

        from rest_framework_simplejwt.tokens import RefreshToken

        self.client_simple = APIClient()
        refresh_simple = RefreshToken.for_user(self.field_op)
        self.client_simple.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_simple.access_token}"
        )
        self.client_simple.force_authenticate(user=self.field_op)

        self.client_strict_mgr = APIClient()
        refresh_mgr = RefreshToken.for_user(self.farm_manager)
        self.client_strict_mgr.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_mgr.access_token}"
        )
        self.client_strict_mgr.force_authenticate(user=self.farm_manager)

        self.client_strict_fin = APIClient()
        refresh_fin = RefreshToken.for_user(self.finance_mgr)
        self.client_strict_fin.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh_fin.access_token}"
        )
        self.client_strict_fin.force_authenticate(user=self.finance_mgr)

    def test_e2e_simple_mode_operations(self):
        from django.utils import timezone

        dlog = DailyLog.objects.create(
            farm=self.farm_simple,
            date=timezone.localdate(),
            notes="Morning session",
            created_by=self.field_op,
        )
        Activity.objects.create(
            log=dlog,
            crop_plan=self.plan,
            created_by=self.field_op,
        )

        response = self.client_simple.get(
            "/api/v1/finance/ledger/",
            HTTP_X_FARM_ID=str(self.farm_simple.id),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "ROUTE_BREACH_SIMPLE_MODE")

        breach_logged = AuditLog.objects.filter(
            actor=self.field_op,
            action="ROUTE_BREACH_ATTEMPT",
        ).exists()
        self.assertTrue(breach_logged)

    def test_e2e_strict_mode_financial_cycle(self):
        ApprovalRule.objects.create(
            farm=self.farm_strict,
            module=ApprovalRule.MODULE_FINANCE,
            action="supplier_settlement",
            min_amount=Decimal("0.0000"),
            max_amount=Decimal("10000.0000"),
            required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
        )

        po = PurchaseOrder.objects.create(
            farm=self.farm_strict,
            vendor_name="AgriSupplies Co",
            total_amount=Decimal("5000.0000"),
            status=PurchaseOrder.Status.RECEIVED,
        )

        settlement = SupplierSettlementService.create_draft(
            user=self.farm_manager,
            purchase_order_id=po.id,
            invoice_reference="INV-001",
        )
        self.assertEqual(settlement.status, SupplierSettlement.STATUS_DRAFT)

        settlement = SupplierSettlementService.submit_review(settlement.id, self.finance_mgr)
        self.assertEqual(settlement.status, SupplierSettlement.STATUS_UNDER_REVIEW)

        from django.contrib.contenttypes.models import ContentType

        req = ApprovalGovernanceService.create_request(
            user=self.farm_manager,
            farm=self.farm_strict,
            module=ApprovalRule.MODULE_FINANCE,
            action="supplier_settlement",
            object_id=str(settlement.id),
            content_type=ContentType.objects.get_for_model(settlement),
            requested_amount=settlement.payable_amount,
        )
        self.assertEqual(req.status, ApprovalRequest.STATUS_PENDING)

        try:
            from rest_framework.exceptions import PermissionDenied

            ApprovalGovernanceService.approve_request(user=self.farm_manager, request_id=req.id)
            self.fail("Maker-checker failed: allowed creator to approve.")
        except PermissionDenied as exc:
            self.assertIn("لا يجوز لمنشئ الطلب اعتماد طلبه نفسه", str(exc))

        ApprovalGovernanceService.approve_request(user=self.finance_mgr, request_id=req.id)

        req.refresh_from_db()
        self.assertEqual(req.status, ApprovalRequest.STATUS_APPROVED)

        Attachment.objects.create(
            farm=self.farm_strict,
            file=SimpleUploadedFile(
                "supplier-settlement.pdf",
                b"%PDF-1.4 strict supplier settlement attachment",
                content_type="application/pdf",
            ),
            uploaded_by=self.sector_director,
            filename_original="supplier-settlement.pdf",
            related_document_type="supplier_settlement",
            document_scope=str(settlement.id),
            malware_scan_status=Attachment.MALWARE_SCAN_PASSED,
        )

        settlement = SupplierSettlementService.approve(settlement.id, self.sector_director)
        self.assertEqual(settlement.status, SupplierSettlement.STATUS_APPROVED)

        print(">> E2E CYCLE COMPLETED SUCCESSFULLY")
        print(f">> SIMPLE Farm Settings: {self.farm_simple.settings.mode}")
        print(f">> STRICT Farm Settings: {self.farm_strict.settings.mode}")
        print(f">> Boundary Breaches Blocked: {AuditLog.objects.filter(action='ROUTE_BREACH_ATTEMPT').count()}")
        print(f">> Supplier Settlement Status: {settlement.status}")
