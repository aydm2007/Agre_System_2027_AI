import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from smart_agri.core.models.farm import Farm
from smart_agri.accounts.models import User, FarmMembership
from smart_agri.finance.models import CostCenter
from smart_agri.inventory.models import PurchaseOrder
from smart_agri.finance.models_supplier_settlement import SupplierSettlement
from smart_agri.finance.services.supplier_settlement_service import SupplierSettlementService
from smart_agri.core.models.log import Attachment

@pytest.fixture
def setup_attachment_data(db):
    farm = Farm.objects.create(name="Attach Farm", slug="attach-farm", tier=Farm.TIER_LARGE)
    # Enable STRICT mode
    from smart_agri.core.models.settings import FarmSettings
    ffm_user = User.objects.create_user(username="ffm", password="password")
    FarmMembership.objects.create(farm=farm, user=ffm_user, role="المدير المالي للمزرعة")
    FarmSettings.objects.create(farm=farm, mode=FarmSettings.MODE_STRICT)

    auth_user = User.objects.create_user(username="auth", password="password")
    FarmMembership.objects.create(farm=farm, user=auth_user, role="مدير القطاع")

    po = PurchaseOrder.objects.create(
        farm=farm,
        vendor_name="Test Vendor",
        total_amount=Decimal('100.00'),
        status=PurchaseOrder.STATUS_RECEIVED,
        created_by=ffm_user
    )

    settlement = SupplierSettlement.objects.create(
        farm=farm,
        purchase_order=po,
        payable_amount=Decimal('100.00'),
        status=SupplierSettlement.STATUS_UNDER_REVIEW,
        created_by=ffm_user,
    )

    return {
        "farm": farm,
        "settlement": settlement,
        "auth_user": auth_user
    }

@pytest.mark.django_db
def test_strict_mode_blocks_approval_without_attachment(setup_attachment_data):
    """
    In STRICT mode, approving a supplier settlement without a valid attachment should fail.
    """
    data = setup_attachment_data
    settlement = data["settlement"]
    user = data["auth_user"]

    with pytest.raises(ValidationError) as excinfo:
        SupplierSettlementService.approve(settlement_id=settlement.id, user=user)
    
    assert "[GOVERNANCE BLOCK]" in str(excinfo.value)
    assert "مرفق سليم" in str(excinfo.value)

@pytest.mark.django_db
def test_strict_mode_allows_approval_with_attachment(setup_attachment_data):
    """
    In STRICT mode, having an attachment with correct metadata allows the approval.
    """
    data = setup_attachment_data
    settlement = data["settlement"]
    user = data["auth_user"]

    # Create dummy attachment
    Attachment.objects.create(
        farm=data["farm"],
        uploaded_by=user,
        related_document_type="supplier_settlement",
        document_scope=str(settlement.id),
        malware_scan_status=Attachment.MALWARE_SCAN_PASSED,
        evidence_class=Attachment.EVIDENCE_CLASS_FINANCIAL,
        is_authoritative_evidence=True,
        filename_original="invoice.pdf",
        mime_type_detected="application/pdf",
        content_hash="dummyhash",
        size_bytes=1024,
        attachment_class=Attachment.EVIDENCE_CLASS_FINANCIAL,
        retention_class=Attachment.EVIDENCE_CLASS_FINANCIAL,
        archive_state=Attachment.ARCHIVE_STATE_HOT,
        scan_state=Attachment.MALWARE_SCAN_PASSED,
        quarantine_state=Attachment.QUARANTINE_STATE_NONE,
        authoritative_at=timezone.now()
    )

    approved = SupplierSettlementService.approve(settlement_id=settlement.id, user=user)
    assert approved.status == SupplierSettlement.STATUS_APPROVED
