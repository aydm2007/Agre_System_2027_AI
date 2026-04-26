import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from smart_agri.core.models import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.accounts.models import FarmMembership
from smart_agri.finance.models import ApprovalRequest, ApprovalRule, ApprovalStageEvent
from smart_agri.finance.services.approval_service import ApprovalGovernanceService
from rest_framework.exceptions import PermissionDenied


@pytest.mark.django_db
class TestSectorLanes(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Test Farm", tier="LARGE")
        self.settings = FarmSettings.objects.create(
            farm=self.farm,
            mode=FarmSettings.MODE_STRICT,
            approval_profile=FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE
        )
        
        # Create users for each role in the ladder
        roles = [
            ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            ApprovalRule.ROLE_SECTOR_REVIEWER,
            ApprovalRule.ROLE_CHIEF_ACCOUNTANT,
            ApprovalRule.ROLE_FINANCE_DIRECTOR,
            ApprovalRule.ROLE_SECTOR_DIRECTOR,
        ]
        
        self.role_users = {}
        for role in roles:
            # Map rule roles to membership roles expected by `user_has_farm_role` etc.
            role_label = ApprovalGovernanceService.ROLE_LABELS.get(role)
            user = User.objects.create_user(username=f"user_{role}", password="pw")
            FarmMembership.objects.create(user=user, farm=self.farm, role=role_label)
            self.role_users[role] = user

        # The creator
        self.creator = User.objects.create_user(username="creator", password="pw")
        FarmMembership.objects.create(user=self.creator, farm=self.farm, role="مدير المزرعة")
        
    def _create_request_for_final_role(self, final_role):
        return ApprovalGovernanceService.create_request(
            user=self.creator,
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="petty_cash_disbursement",
            requested_amount=Decimal("1000000.0000") # High amount to trigger full chain if rules existed, but we force final_role
        )

    def test_sector_accountant_first_review(self):
        """Lane 1: محاسب القطاع does first review (after FFM)."""
        # Force a request starting directly at SECTOR_ACCOUNTANT
        req = self._create_request_for_final_role(ApprovalRule.ROLE_SECTOR_DIRECTOR)
        # Fast-forward FFM
        ApprovalGovernanceService.approve_request(
            user=self.role_users[ApprovalRule.ROLE_FARM_FINANCE_MANAGER], 
            request_id=req.id, 
            note="FFM approved"
        )
        req.refresh_from_db()
        
        self.assertEqual(req.required_role, ApprovalRule.ROLE_SECTOR_ACCOUNTANT)
        
        # Attempt approve with wrong role (e.g., SECTOR_REVIEWER)
        reviewer_user = self.role_users[ApprovalRule.ROLE_SECTOR_REVIEWER]
        with self.assertRaises(PermissionDenied):
            ApprovalGovernanceService.approve_request(user=reviewer_user, request_id=req.id)
            
        # Approve with right role
        accountant_user = self.role_users[ApprovalRule.ROLE_SECTOR_ACCOUNTANT]
        ApprovalGovernanceService.approve_request(user=accountant_user, request_id=req.id)
        
        req.refresh_from_db()
        self.assertEqual(req.required_role, ApprovalRule.ROLE_SECTOR_REVIEWER)
        
        # Check event
        event = ApprovalStageEvent.objects.filter(request=req).order_by("-id").first()
        self.assertEqual(event.action_type, ApprovalStageEvent.ACTION_STAGE_APPROVED)
        self.assertEqual(event.role, ApprovalRule.ROLE_SECTOR_ACCOUNTANT)


    def test_sector_reviewer_second_review(self):
        """Lane 2: مراجع القطاع does second review."""
        req = self._create_request_for_final_role(ApprovalRule.ROLE_SECTOR_DIRECTOR)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_FARM_FINANCE_MANAGER], request_id=req.id)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_SECTOR_ACCOUNTANT], request_id=req.id)
        
        req.refresh_from_db()
        self.assertEqual(req.required_role, ApprovalRule.ROLE_SECTOR_REVIEWER)
        
        # Wrong role
        with self.assertRaises(PermissionDenied):
            ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_CHIEF_ACCOUNTANT], request_id=req.id)
            
        # Right role
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_SECTOR_REVIEWER], request_id=req.id)
        req.refresh_from_db()
        self.assertEqual(req.required_role, ApprovalRule.ROLE_CHIEF_ACCOUNTANT)

    def test_sector_chief_accountant_signoff(self):
        """Lane 3: رئيس حسابات القطاع does accounting sign-off."""
        req = self._create_request_for_final_role(ApprovalRule.ROLE_SECTOR_DIRECTOR)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_FARM_FINANCE_MANAGER], request_id=req.id)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_SECTOR_ACCOUNTANT], request_id=req.id)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_SECTOR_REVIEWER], request_id=req.id)
        
        req.refresh_from_db()
        self.assertEqual(req.required_role, ApprovalRule.ROLE_CHIEF_ACCOUNTANT)
        
        # Right role
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_CHIEF_ACCOUNTANT], request_id=req.id)
        req.refresh_from_db()
        self.assertEqual(req.required_role, ApprovalRule.ROLE_FINANCE_DIRECTOR)

    def test_sector_finance_director_final(self):
        """Lane 4: المدير المالي لقطاع المزارع does final approval (if final)."""
        # Create request where FINANCE_DIRECTOR is final
        req = self._create_request_for_final_role(ApprovalRule.ROLE_SECTOR_DIRECTOR)
        # Advance to Finance Director
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_FARM_FINANCE_MANAGER], request_id=req.id)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_SECTOR_ACCOUNTANT], request_id=req.id)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_SECTOR_REVIEWER], request_id=req.id)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_CHIEF_ACCOUNTANT], request_id=req.id)
        
        req.refresh_from_db()
        self.assertEqual(req.required_role, ApprovalRule.ROLE_FINANCE_DIRECTOR)
        
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_FINANCE_DIRECTOR], request_id=req.id)
        req.refresh_from_db()
        self.assertEqual(req.required_role, ApprovalRule.ROLE_SECTOR_DIRECTOR)

    def test_sector_director_when_required(self):
        """Lane 5: مدير القطاع when policy requires."""
        req = self._create_request_for_final_role(ApprovalRule.ROLE_SECTOR_DIRECTOR)
        # Advance all the way
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_FARM_FINANCE_MANAGER], request_id=req.id)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_SECTOR_ACCOUNTANT], request_id=req.id)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_SECTOR_REVIEWER], request_id=req.id)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_CHIEF_ACCOUNTANT], request_id=req.id)
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_FINANCE_DIRECTOR], request_id=req.id)
        
        req.refresh_from_db()
        self.assertEqual(req.required_role, ApprovalRule.ROLE_SECTOR_DIRECTOR)
        
        ApprovalGovernanceService.approve_request(user=self.role_users[ApprovalRule.ROLE_SECTOR_DIRECTOR], request_id=req.id)
        req.refresh_from_db()
        
        self.assertEqual(req.status, ApprovalRequest.STATUS_APPROVED)
        event = ApprovalStageEvent.objects.filter(request=req).order_by("-id").first()
        self.assertEqual(event.action_type, ApprovalStageEvent.ACTION_FINAL_APPROVED)
