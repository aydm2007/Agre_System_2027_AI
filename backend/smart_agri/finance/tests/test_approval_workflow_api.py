from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import ApprovalRequest, ApprovalRule, ApprovalStageEvent
from smart_agri.finance.services.approval_service import ApprovalGovernanceService


class ApprovalWorkflowApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="approver", password="pass1234")
        self.user.user_permissions.add(Permission.objects.get(codename="can_approve_finance_request"))
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name="Sardud Farm")
        FarmSettings.objects.create(farm=self.farm, mode=FarmSettings.MODE_STRICT)
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="مدير المزرعة")
        self.client.credentials(HTTP_X_FARM_ID=str(self.farm.id))

        ApprovalRule.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="expense_posting",
            min_amount=Decimal("0.0000"),
            required_role=ApprovalRule.ROLE_MANAGER,
            is_active=True,
        )

    def test_approve_requires_idempotency_key(self):
        req = ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="expense_posting",
            requested_amount=Decimal("100.0000"),
            requested_by=User.objects.create_user(username='maker1'),
            required_role=ApprovalRule.ROLE_MANAGER,
            final_required_role=ApprovalRule.ROLE_MANAGER,
            status=ApprovalRequest.STATUS_PENDING,
        )
        resp = self.client.post(f"/api/v1/finance/approval-requests/{req.id}/approve/", {}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_approve_replays_cached_response_on_duplicate_key(self):
        req = ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action="expense_posting",
            requested_amount=Decimal("250.0000"),
            requested_by=User.objects.create_user(username='maker2'),
            required_role=ApprovalRule.ROLE_MANAGER,
            final_required_role=ApprovalRule.ROLE_MANAGER,
            status=ApprovalRequest.STATUS_PENDING,
        )
        headers = {"HTTP_X_IDEMPOTENCY_KEY": "approval-approve-001"}

        first = self.client.post(
            f"/api/v1/finance/approval-requests/{req.id}/approve/",
            {},
            format="json",
            **headers,
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json().get("status"), "approved")

        second = self.client.post(
            f"/api/v1/finance/approval-requests/{req.id}/approve/",
            {},
            format="json",
            **headers,
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json(), first.json())

        req.refresh_from_db()
        self.assertEqual(req.status, ApprovalRequest.STATUS_APPROVED)

    def test_multistage_request_advances_role_before_final_approval(self):
        maker = User.objects.create_user(username='maker3')
        farm_finance = User.objects.create_user(username='farm_finance_stage', password='pass1234')
        farm_finance.user_permissions.add(Permission.objects.get(codename='can_approve_finance_request'))
        FarmMembership.objects.create(user=farm_finance, farm=self.farm, role='المدير المالي للمزرعة')
        self.client.force_authenticate(farm_finance)
        req = ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('300000.0000'),
            requested_by=maker,
            required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            final_required_role=ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            current_stage=1,
            total_stages=2,
            status=ApprovalRequest.STATUS_PENDING,
        )
        headers = {"HTTP_X_IDEMPOTENCY_KEY": "approval-stage-001"}
        resp = self.client.post(f"/api/v1/finance/approval-requests/{req.id}/approve/", {}, format='json', **headers)
        self.assertEqual(resp.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, ApprovalRequest.STATUS_PENDING)
        self.assertEqual(req.current_stage, 2)
        self.assertEqual(req.required_role, ApprovalRule.ROLE_SECTOR_ACCOUNTANT)
        self.assertEqual(len(req.approval_history), 1)

    def test_requester_cannot_self_approve(self):
        requester = User.objects.create_user(username='maker4', password='pass1234')
        requester.user_permissions.add(Permission.objects.get(codename='can_approve_finance_request'))
        FarmMembership.objects.create(user=requester, farm=self.farm, role='مدير المزرعة')
        self.client.force_authenticate(requester)
        req = ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('100.0000'),
            requested_by=requester,
            required_role=ApprovalRule.ROLE_MANAGER,
            final_required_role=ApprovalRule.ROLE_MANAGER,
            status=ApprovalRequest.STATUS_PENDING,
        )
        resp = self.client.post(
            f"/api/v1/finance/approval-requests/{req.id}/approve/",
            {},
            format='json',
            HTTP_X_IDEMPOTENCY_KEY='approval-self-001',
        )
        self.assertEqual(resp.status_code, 403)


    def test_queue_summary_endpoint_returns_lane_metrics(self):
        scoped_user = User.objects.create_user(username='sector_summary', password='pass1234')
        scoped_user.user_permissions.add(Permission.objects.get(codename='can_approve_finance_request'))
        FarmMembership.objects.create(user=scoped_user, farm=self.farm, role='محاسب القطاع')
        client = APIClient()
        client.force_authenticate(scoped_user)
        client.credentials(HTTP_X_FARM_ID=str(self.farm.id))
        ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('400000.0000'),
            requested_by=User.objects.create_user(username='maker5'),
            required_role=ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            final_required_role=ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            current_stage=1,
            total_stages=2,
            status=ApprovalRequest.STATUS_PENDING,
        )
        resp = client.get('/api/v1/finance/approval-requests/queue-summary/')
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertGreaterEqual(payload['pending_count'], 1)
        self.assertTrue(any(lane['role'] == ApprovalRule.ROLE_SECTOR_ACCOUNTANT for lane in payload['lanes']))
        self.assertIn('blocked_count', payload)
        self.assertIn('lane_health_counts', payload)

    def test_role_workbench_filters_by_lane_health(self):
        req = ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('400000.0000'),
            requested_by=User.objects.create_user(username='maker-health'),
            required_role=ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            final_required_role=ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            current_stage=1,
            total_stages=2,
            status=ApprovalRequest.STATUS_PENDING,
        )
        req.created_at = req.updated_at = req.updated_at - timedelta(days=5)
        req.save(update_fields=['created_at', 'updated_at'])
        resp = self.client.get('/api/v1/finance/approval-requests/role-workbench/?lane_health=attention')
        self.assertEqual(resp.status_code, 200)
        rows = resp.json()['rows']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['lane_health'], 'attention')

    def test_attention_feed_returns_overdue_item(self):
        req = ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('250000.0000'),
            requested_by=User.objects.create_user(username='maker-attn'),
            required_role=ApprovalRule.ROLE_MANAGER,
            final_required_role=ApprovalRule.ROLE_MANAGER,
            current_stage=1,
            total_stages=1,
            status=ApprovalRequest.STATUS_PENDING,
        )
        req.created_at = req.updated_at = req.updated_at - timedelta(days=5)
        req.save(update_fields=['created_at', 'updated_at'])
        resp = self.client.get('/api/v1/finance/approval-requests/attention-feed/?kind=approval_overdue')
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertGreaterEqual(payload['count'], 1)
        self.assertEqual(payload['items'][0]['kind'], 'approval_overdue')

    def test_role_workbench_summary_endpoint_returns_summary(self):
        ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('150000.0000'),
            requested_by=User.objects.create_user(username='maker-summary'),
            required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            final_required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            current_stage=1,
            total_stages=1,
            status=ApprovalRequest.STATUS_PENDING,
        )
        resp = self.client.get('/api/v1/finance/approval-requests/role-workbench-summary/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('summary', resp.json())
        self.assertIn('rows', resp.json()['summary'])

    def test_sector_dashboard_endpoint_returns_rollups(self):
        ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('175000.0000'),
            requested_by=User.objects.create_user(username='maker-dashboard'),
            required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            final_required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            current_stage=1,
            total_stages=1,
            status=ApprovalRequest.STATUS_PENDING,
        )
        resp = self.client.get('/api/v1/finance/approval-requests/sector-dashboard/')
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertIn('kpis', payload)
        self.assertIn('top_farms', payload)
        self.assertIn('blocked_buckets', payload)

    def test_policy_impact_endpoint_returns_affected_farms(self):
        ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('210000.0000'),
            requested_by=User.objects.create_user(username='maker-policy-impact'),
            required_role=ApprovalRule.ROLE_MANAGER,
            final_required_role=ApprovalRule.ROLE_MANAGER,
            current_stage=1,
            total_stages=1,
            status=ApprovalRequest.STATUS_PENDING,
        )
        resp = self.client.get('/api/v1/finance/approval-requests/policy-impact/')
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertIn('approval_profile_counts', payload)
        self.assertGreaterEqual(len(payload['affected_farms']), 1)

    def test_farm_governance_endpoint_returns_farm_scoped_snapshot(self):
        ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('220000.0000'),
            requested_by=User.objects.create_user(username='maker-farm-governance'),
            required_role=ApprovalRule.ROLE_MANAGER,
            final_required_role=ApprovalRule.ROLE_MANAGER,
            current_stage=1,
            total_stages=1,
            status=ApprovalRequest.STATUS_PENDING,
        )
        resp = self.client.get(f'/api/v1/finance/approval-requests/farm-governance/?farm={self.farm.id}')
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload['farm_id'], self.farm.id)
        self.assertIn('lane_summary', payload)
        self.assertIn('policy_summary', payload)

    def test_runtime_governance_endpoint_returns_operational_snapshot(self):
        ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('230000.0000'),
            requested_by=User.objects.create_user(username='maker-runtime-governance'),
            required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            final_required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            current_stage=1,
            total_stages=1,
            status=ApprovalRequest.STATUS_PENDING,
        )
        resp = self.client.get('/api/v1/finance/approval-requests/runtime-governance/')
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertIn('pending_requests', payload)
        self.assertIn('blocked_reasons', payload)
        self.assertIn('lane_health_totals', payload)
        self.assertIn('request_headers', payload)

    def test_runtime_governance_detail_endpoint_returns_detail_rows(self):
        req = ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('230000.0000'),
            requested_by=User.objects.create_user(username='maker-runtime-governance-detail'),
            required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            final_required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            current_stage=1,
            total_stages=1,
            status=ApprovalRequest.STATUS_PENDING,
        )
        req.created_at = req.updated_at = req.updated_at - timedelta(days=3)
        req.save(update_fields=['created_at', 'updated_at'])
        resp = self.client.get('/api/v1/finance/approval-requests/runtime-governance/detail/')
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertIn('detail_rows', payload)
        self.assertGreaterEqual(payload['filtered_total'], 1)

    def test_farm_ops_endpoint_returns_scoped_detail(self):
        ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('230000.0000'),
            requested_by=User.objects.create_user(username='maker-farm-ops'),
            required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            final_required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            current_stage=1,
            total_stages=1,
            status=ApprovalRequest.STATUS_PENDING,
        )
        resp = self.client.get(f'/api/v1/finance/approval-requests/farm-ops/?farm={self.farm.id}')
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload['farm_id'], self.farm.id)
        self.assertIn('outbox', payload)
        self.assertIn('attachment_runtime', payload)

    @patch('smart_agri.finance.api_approval.ApprovalGovernanceService.request_trace')
    def test_request_trace_endpoint_returns_trace_payload(self, trace_mock):
        trace_mock.return_value = {
            'request': {'id': 777, 'status': 'PENDING'},
            'queue_snapshot': {'lane_health': 'attention'},
            'workflow_blueprint': {'stage_chain': []},
            'stage_events': [],
            'policy_context': {'effective_mode': 'STRICT'},
            'blockers': ['approval_overdue'],
            'correlation_id': 'corr-trace-777',
        }
        with patch('smart_agri.finance.api_approval.ApprovalRequestViewSet.get_queryset') as queryset_mock:
            queryset_mock.return_value.filter.return_value.exists.return_value = True
            resp = self.client.get('/api/v1/finance/approval-requests/request-trace/?request_id=777')
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload['request']['id'], 777)
        self.assertEqual(payload['correlation_id'], 'corr-trace-777')

    @patch('smart_agri.finance.api_approval.OpsRemediationService.dry_run_governance_maintenance')
    def test_runtime_governance_dry_run_maintenance_endpoint(self, dry_run_mock):
        dry_run_mock.return_value = {'action_id': 'ops-3', 'status': 'completed', 'processed': 0, 'skipped': 0, 'failed': 0}
        resp = self.client.post(
            '/api/v1/finance/approval-requests/runtime-governance/dry-run-maintenance/',
            {},
            format='json',
            HTTP_HOST='localhost',
            HTTP_X_FORWARDED_PROTO='https',
            HTTP_X_IDEMPOTENCY_KEY='approval-runtime-dry-run-001',
            secure=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'completed')

    def test_my_queue_endpoint_only_returns_requests_user_can_approve(self):
        scoped_user = User.objects.create_user(username='sector_accountant', password='pass1234')
        FarmMembership.objects.create(user=scoped_user, farm=self.farm, role='محاسب القطاع')
        client = APIClient()
        client.force_authenticate(scoped_user)
        client.credentials(HTTP_X_FARM_ID=str(self.farm.id))

        ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('120000.0000'),
            requested_by=User.objects.create_user(username='maker6'),
            required_role=ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            final_required_role=ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            current_stage=2,
            total_stages=2,
            status=ApprovalRequest.STATUS_PENDING,
        )
        ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('120000.0000'),
            requested_by=User.objects.create_user(username='maker7'),
            required_role=ApprovalRule.ROLE_SECTOR_DIRECTOR,
            final_required_role=ApprovalRule.ROLE_SECTOR_DIRECTOR,
            current_stage=1,
            total_stages=4,
            status=ApprovalRequest.STATUS_PENDING,
        )
        resp = client.get('/api/v1/finance/approval-requests/my-queue/')
        self.assertEqual(resp.status_code, 200)
        rows = resp.json().get('results', resp.json())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['required_role'], ApprovalRule.ROLE_SECTOR_ACCOUNTANT)


    def test_timeline_endpoint_returns_stage_events(self):
        req = ApprovalRequest.objects.create(
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('120000.0000'),
            requested_by=User.objects.create_user(username='maker8'),
            required_role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            final_required_role=ApprovalRule.ROLE_SECTOR_ACCOUNTANT,
            current_stage=1,
            total_stages=2,
            status=ApprovalRequest.STATUS_PENDING,
        )
        ApprovalStageEvent.objects.create(
            request=req,
            stage_number=1,
            role=ApprovalRule.ROLE_FARM_FINANCE_MANAGER,
            action_type=ApprovalStageEvent.ACTION_CREATED,
            actor=req.requested_by,
            note='created',
        )
        resp = self.client.get(f'/api/v1/finance/approval-requests/{req.id}/timeline/')
        self.assertEqual(resp.status_code, 200)
        rows = resp.json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['action_type'], ApprovalStageEvent.ACTION_CREATED)

    def test_create_request_records_stage_event(self):
        req = ApprovalGovernanceService.create_request(
            user=self.user,
            farm=self.farm,
            module=ApprovalRule.MODULE_FINANCE,
            action='expense_posting',
            requested_amount=Decimal('50.0000'),
        )
        self.assertEqual(req.stage_events.count(), 1)
        event = req.stage_events.first()
        self.assertEqual(event.action_type, ApprovalStageEvent.ACTION_CREATED)
