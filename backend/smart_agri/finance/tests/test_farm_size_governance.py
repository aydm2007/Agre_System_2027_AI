from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from smart_agri.core.models import Farm
from smart_agri.accounts.models import FarmMembership
from smart_agri.finance.models import ApprovalRule
from smart_agri.finance.services.approval_service import ApprovalGovernanceService


class TestFarmSizeGovernance(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username="creator", password="pw")
        
    def test_medium_farm_requires_ffm(self):
        farm_medium = Farm.objects.create(name="Medium Farm", tier="MEDIUM")
        
        # User adds themselves as Manager
        FarmMembership.objects.create(user=self.creator, farm=farm_medium, role="مدير المزرعة")
        
        # Creating request should fail because no FFM exists
        with self.assertRaises(ValidationError) as context:
            ApprovalGovernanceService.create_request(
                user=self.creator,
                farm=farm_medium,
                module=ApprovalRule.MODULE_FINANCE,
                action="petty_cash_disbursement",
                requested_amount="50000.0000"
            )
            
        self.assertIn("تتطلب تعيين مدير مالي للمزرعة", str(context.exception))
        
        # Now add an FFM
        ffm_user = User.objects.create_user(username="ffm", password="password")
        FarmMembership.objects.create(user=ffm_user, farm=farm_medium, role="المدير المالي للمزرعة")
        
        # Should succeed
        req = ApprovalGovernanceService.create_request(
            user=self.creator,
            farm=farm_medium,
            module=ApprovalRule.MODULE_FINANCE,
            action="petty_cash_disbursement",
            requested_amount="50000.0000"
        )
        self.assertIsNotNone(req.id)

    def test_large_farm_requires_ffm(self):
        farm_large = Farm.objects.create(name="Large Farm", tier="LARGE")
        FarmMembership.objects.create(user=self.creator, farm=farm_large, role="مدير المزرعة")
        
        # Should fail
        with self.assertRaises(ValidationError) as context:
            ApprovalGovernanceService.create_request(
                user=self.creator,
                farm=farm_large,
                module=ApprovalRule.MODULE_FINANCE,
                action="petty_cash_disbursement",
                requested_amount="50000.0000"
            )
        self.assertIn("تتطلب تعيين مدير مالي للمزرعة", str(context.exception))
        
        # Add FFM
        ffm_user = User.objects.create_user(username="ffm_large", password="password")
        FarmMembership.objects.create(user=ffm_user, farm=farm_large, role="المدير المالي للمزرعة")
        
        req = ApprovalGovernanceService.create_request(
            user=self.creator,
            farm=farm_large,
            module=ApprovalRule.MODULE_FINANCE,
            action="petty_cash_disbursement",
            requested_amount="50000.0000"
        )
        self.assertIsNotNone(req.id)
        
    def test_small_farm_does_not_strictly_require_ffm_by_default(self):
        farm_small = Farm.objects.create(name="Small Farm", tier="SMALL")
        FarmMembership.objects.create(user=self.creator, farm=farm_small, role="مدير المزرعة")
        
        # Small farm does not require FFM for creation if it's tier Policy allows it
        # Actually it depends on the FarmTieringPolicyService, but SMALL tier defaults to NOT requiring FFM.
        req = ApprovalGovernanceService.create_request(
            user=self.creator,
            farm=farm_small,
            module=ApprovalRule.MODULE_FINANCE,
            action="petty_cash_disbursement",
            requested_amount="50000.0000"
        )
        self.assertIsNotNone(req.id)
