from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal

from smart_agri.core.models import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.accounts.models import FarmMembership
from smart_agri.finance.models import ApprovalRequest, ApprovalRule, ApprovalStageEvent
from smart_agri.finance.services.approval_service import ApprovalGovernanceService


class TestForensicApprovalTimeline(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username="creator", password="pw")
        self.approver = User.objects.create_user(username="approver", password="pw")
        
        self.farm = Farm.objects.create(name="Timeline Farm", tier="SMALL")
        FarmSettings.objects.create(farm=self.farm, mode=FarmSettings.MODE_STRICT)
        
        FarmMembership.objects.create(user=self.creator, farm=self.farm, role="مدير المزرعة")
        # Final role is FFM based on small farm rules
        FarmMembership.objects.create(user=self.approver, farm=self.farm, role="المدير المالي للمزرعة")

    def test_stage_events_created_on_request(self):
        req = ApprovalGovernanceService.create_request(
            user=self.creator,
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="expense_posting",
            requested_amount=Decimal("1000.00")
        )
        
        events = ApprovalStageEvent.objects.filter(request=req)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first().action_type, ApprovalStageEvent.ACTION_CREATED)
        self.assertEqual(events.first().role, ApprovalRule.ROLE_FARM_FINANCE_MANAGER)

    def test_stage_events_on_each_stage_pass(self):
        req = ApprovalGovernanceService.create_request(
            user=self.creator,
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="expense_posting",
            requested_amount=Decimal("1000.00")
        )
        
        ApprovalGovernanceService.approve_request(user=self.approver, request_id=req.id)
        
        events = ApprovalStageEvent.objects.filter(request=req).order_by('id')
        self.assertEqual(events.count(), 2)
        self.assertEqual(events[0].action_type, ApprovalStageEvent.ACTION_CREATED)
        self.assertEqual(events[1].action_type, ApprovalStageEvent.ACTION_FINAL_APPROVED)
        
    def test_stage_events_on_rejection(self):
        req = ApprovalGovernanceService.create_request(
            user=self.creator,
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="expense_posting",
            requested_amount=Decimal("1000.00")
        )
        
        ApprovalGovernanceService.reject_request(user=self.approver, request_id=req.id, reason="No funds")
        
        events = ApprovalStageEvent.objects.filter(request=req).order_by('id')
        self.assertEqual(events.count(), 2)
        self.assertEqual(events.last().action_type, ApprovalStageEvent.ACTION_REJECTED)
        self.assertEqual(events.last().note, "No funds")
        
    def test_stage_events_on_reopen(self):
        req = ApprovalGovernanceService.create_request(
            user=self.creator,
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="expense_posting",
            requested_amount=Decimal("1000.00")
        )
        
        ApprovalGovernanceService.reject_request(user=self.approver, request_id=req.id, reason="No funds")
        ApprovalGovernanceService.reopen_request(user=self.creator, request_id=req.id, reason="Fixed")
        
        events = ApprovalStageEvent.objects.filter(request=req).order_by('id')
        self.assertEqual(events.count(), 3)
        self.assertEqual(events.last().action_type, ApprovalStageEvent.ACTION_REOPENED)
        self.assertEqual(events.last().note, "Fixed")

    def test_timeline_independent_of_ui_state(self):
        req = ApprovalGovernanceService.create_request(
            user=self.creator,
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="expense_posting",
            requested_amount=Decimal("1000.00")
        )
        ApprovalGovernanceService.approve_request(user=self.approver, request_id=req.id)
        
        req.refresh_from_db()
        self.assertEqual(req.status, ApprovalRequest.STATUS_APPROVED)
        
        # Even if status is forced (e.g. by admin) to something else, events remain untouched
        ApprovalRequest.objects.filter(id=req.id).update(status=ApprovalRequest.STATUS_PENDING)
        
        events = ApprovalStageEvent.objects.filter(request=req)
        # 2 events from creation and approval
        self.assertEqual(events.count(), 2)
        
        payload = ApprovalGovernanceService.stage_events_payload(req=req)
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[1]['action'], ApprovalStageEvent.ACTION_FINAL_APPROVED)
