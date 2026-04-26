from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import ApprovalRequest, ApprovalRule, ApprovalStageEvent


class ApprovalOverrideAndReopenApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.farm = Farm.objects.create(name="Governed Farm")
        FarmSettings.objects.create(farm=self.farm, mode=FarmSettings.MODE_STRICT)
        self.client.credentials(HTTP_X_FARM_ID=str(self.farm.id))

        self.requester = User.objects.create_user(username="maker", password="pass1234")
        FarmMembership.objects.create(user=self.requester, farm=self.farm, role="محاسب المزرعة")

        self.final_authority = User.objects.create_user(username="sector_dir", password="pass1234")
        self.final_authority.user_permissions.add(
            Permission.objects.get(codename="can_approve_finance_request")
        )
        FarmMembership.objects.create(user=self.final_authority, farm=self.farm, role="مدير القطاع")

        self.stage_actor = User.objects.create_user(username="farm_finance_mgr", password="pass1234")
        self.stage_actor.user_permissions.add(
            Permission.objects.get(codename="can_approve_finance_request")
        )
        FarmMembership.objects.create(
            user=self.stage_actor,
            farm=self.farm,
            role="المدير المالي للمزرعة",
        )

        ApprovalRule.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="supplier_settlement_posting",
            min_amount=Decimal("0.0000"),
            required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            is_active=True,
        )

    def _make_request(self, *, status=ApprovalRequest.STATUS_PENDING):
        return ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="supplier_settlement_posting",
            requested_amount=Decimal("250000.0000"),
            requested_by=self.requester,
            required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            final_required_role=ApprovalRule.ROLE_SECTOR_DIRECTOR,
            current_stage=1,
            total_stages=4,
            status=status,
            rejection_reason="missing evidence" if status == ApprovalRequest.STATUS_REJECTED else "",
        )

    def test_override_stage_requires_reason_and_records_event(self):
        req = self._make_request()
        self.client.force_authenticate(self.final_authority)

        missing_reason = self.client.post(
            f"/api/v1/finance/approval-requests/{req.id}/override-stage/",
            {},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="override-001",
        )
        self.assertEqual(missing_reason.status_code, 400)

        resp = self.client.post(
            f"/api/v1/finance/approval-requests/{req.id}/override-stage/",
            {"reason": "sector override for remote site"},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="override-002",
        )
        self.assertEqual(resp.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, ApprovalRequest.STATUS_PENDING)
        self.assertEqual(req.current_stage, 2)
        self.assertEqual(req.required_role, ApprovalRule.ROLE_SECTOR_ACCOUNTANT)
        self.assertTrue(
            ApprovalStageEvent.objects.filter(
                request=req,
                action_type=ApprovalStageEvent.ACTION_OVERRIDDEN,
            ).exists()
        )

    def test_matching_stage_actor_must_not_use_override(self):
        req = self._make_request()
        self.client.force_authenticate(self.stage_actor)
        resp = self.client.post(
            f"/api/v1/finance/approval-requests/{req.id}/override-stage/",
            {"reason": "should fail"},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="override-003",
        )
        self.assertEqual(resp.status_code, 400)

    def test_reopen_rejected_request_resets_stage_and_records_event(self):
        req = self._make_request(status=ApprovalRequest.STATUS_REJECTED)
        self.client.force_authenticate(self.requester)
        resp = self.client.post(
            f"/api/v1/finance/approval-requests/{req.id}/reopen/",
            {"reason": "missing attachments completed"},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="reopen-001",
        )
        self.assertEqual(resp.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, ApprovalRequest.STATUS_PENDING)
        self.assertEqual(req.current_stage, 1)
        self.assertEqual(req.required_role, ApprovalRule.ROLE_FARM_FINANCE_MANAGER)
        self.assertEqual(req.rejection_reason, "")
        self.assertTrue(
            ApprovalStageEvent.objects.filter(
                request=req,
                action_type=ApprovalStageEvent.ACTION_REOPENED,
            ).exists()
        )

    def test_same_actor_must_not_clear_more_than_one_stage(self):
        req = self._make_request()
        req.approval_history = [
            {
                "actor_id": self.stage_actor.id,
                "decision": "APPROVED_STAGE",
                "role": ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
                "at": "2026-03-19T00:00:00+00:00",
            }
        ]
        req.current_stage = 2
        req.required_role = ApprovalRule.ROLE_SECTOR_ACCOUNTANT
        req.save(update_fields=["approval_history", "current_stage", "required_role"])
        membership = FarmMembership.objects.get(user=self.stage_actor, farm=self.farm)
        membership.role = "محاسب القطاع"
        membership.save(update_fields=["role"])
        self.client.force_authenticate(self.stage_actor)
        resp = self.client.post(
            f"/api/v1/finance/approval-requests/{req.id}/approve/",
            {"note": "second stage attempt by same actor"},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="approve-duplicate-actor",
        )
        self.assertEqual(resp.status_code, 403)

    def test_request_creator_cannot_self_approve(self):
        req = self._make_request()
        self.client.force_authenticate(self.requester)
        resp = self.client.post(
            f"/api/v1/finance/approval-requests/{req.id}/approve/",
            {"note": "self approval attempt"},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="approve-self-actor",
        )
        self.assertEqual(resp.status_code, 403)
