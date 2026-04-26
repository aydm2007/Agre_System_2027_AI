from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import ApprovalRequest
from smart_agri.finance.services.approval_service import ApprovalGovernanceService


class RoleWorkbenchSnapshotTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name='Farm A', tier='MEDIUM')
        FarmSettings.objects.create(farm=self.farm)
        self.user = User.objects.create_user(username='req', password='pass')
        self.req = ApprovalRequest.objects.create(
            farm=self.farm,
            module='FINANCE',
            action='settlement',
            requested_amount=Decimal('250000.0000'),
            required_role='SECTOR_ACCOUNTANT',
            final_required_role='FINANCE_DIRECTOR',
            current_stage=2,
            total_stages=5,
            status='PENDING',
            requested_by=self.user,
        )

    def test_role_workbench_groups_pending_requests(self):
        payload = ApprovalGovernanceService.role_workbench_snapshot()
        self.assertTrue(payload['rows'])
        self.assertEqual(payload['rows'][0]['farm_id'], self.farm.id)
        self.assertEqual(payload['rows'][0]['role'], 'SECTOR_ACCOUNTANT')
