from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import ApprovalRule
from smart_agri.finance.services.approval_service import ApprovalGovernanceService


class V16GovernanceMaintenanceTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Remote Farm")
        FarmSettings.objects.create(
            farm=self.farm,
            approval_profile=FarmSettings.APPROVAL_PROFILE_BASIC,
            remote_site=True,
            weekly_remote_review_required=True,
            single_finance_officer_allowed=True,
        )
        self.user = User.objects.create_user(username="director", password="pass1234")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="مدير القطاع")

    def test_basic_profile_shortens_role_chain(self):
        req = ApprovalGovernanceService.create_request(
            user=self.user,
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('120000.0000'),
        )
        self.assertEqual(req.required_role, ApprovalRule.ROLE_FARM_FINANCE_MANAGER)
        self.assertEqual(req.total_stages, 2)

    def test_maintenance_summary_reports_remote_review_gap(self):
        ApprovalGovernanceService.create_request(
            user=self.user,
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('50.0000'),
        )
        summary = ApprovalGovernanceService.maintenance_summary()
        self.assertGreaterEqual(summary['pending_requests'], 1)
        self.assertGreaterEqual(summary['remote_farms_due_review'], 1)
