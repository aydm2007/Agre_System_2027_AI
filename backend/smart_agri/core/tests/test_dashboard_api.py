from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from unittest.mock import patch
from smart_agri.core.models import Farm, Employee, EmploymentContract, CropPlan, Item, ItemInventory
from rest_framework.test import APIClient

class DashboardTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='manager', password='password')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.farm = Farm.objects.create(name="Dashboard Farm", total_area=100)
        
        # Data for Payroll Summary
        emp = Employee.objects.create(farm=self.farm, first_name="Ali", last_name="X", employee_id="E010", role=Employee.TYPE_WORKER)
        EmploymentContract.objects.create(
            employee=emp, 
            start_date="2024-01-01", 
            basic_salary=1000, 
            housing_allowance=200, 
            transport_allowance=100
        )
        # Total Burn: 1300
        
        # Data for Farm Summary
        CropPlan.objects.create(farm=self.farm, area=10, status='active', date_planted="2024-01-01")
        
        item = Item.objects.create(name="Fertilizer", unit_price=50, type='material')
        ItemInventory.objects.create(farm=self.farm, item=item, qty=10) 
        # Stock Value: 50 * 10 = 500

    def test_payroll_summary(self):
        url = f'/api/v1/dashboard/payroll_summary/?farm_id={self.farm.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['headcount'], 1)
        self.assertEqual(response.data['monthly_burn_rate'], 1300)

    def test_farm_summary(self):
        url = f'/api/v1/dashboard/farm_summary/?farm_id={self.farm.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['active_plans'], 1)
        self.assertEqual(response.data['total_stock_value'], 500)

    @patch('smart_agri.core.api.dashboard.OpsHealthService.release_health_snapshot')
    def test_release_health_endpoint(self, snapshot_mock):
        snapshot_mock.return_value = {'severity': 'healthy', 'all_pass': True}
        response = self.client.get('/api/v1/dashboard/release-health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['severity'], 'healthy')

    @patch('smart_agri.core.api.dashboard.OpsHealthService.release_health_detail_snapshot')
    def test_release_health_detail_endpoint(self, snapshot_mock):
        snapshot_mock.return_value = {'severity': 'attention', 'detail_rows': []}
        response = self.client.get('/api/v1/dashboard/release-health/detail/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('detail_rows', response.data)

    @patch('smart_agri.core.api.dashboard.OpsHealthService.integration_outbox_health_snapshot')
    def test_outbox_health_endpoint(self, snapshot_mock):
        snapshot_mock.return_value = {'severity': 'attention', 'dead_letter_count': 1}
        response = self.client.get('/api/v1/dashboard/outbox-health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['dead_letter_count'], 1)

    @patch('smart_agri.core.api.dashboard.OpsHealthService.integration_outbox_detail_snapshot')
    def test_outbox_health_detail_endpoint(self, snapshot_mock):
        snapshot_mock.return_value = {'severity': 'attention', 'detail_rows': [{'id': 1}], 'filtered_total': 1}
        response = self.client.get(f'/api/v1/dashboard/outbox-health/detail/?farm_id={self.farm.id}&limit=10')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['filtered_total'], 1)

    @patch('smart_agri.core.api.dashboard.OpsRemediationService.retry_outbox_events')
    def test_outbox_health_retry_endpoint(self, retry_mock):
        retry_mock.return_value = {'action_id': 'ops-1', 'status': 'completed', 'processed': 1, 'skipped': 0, 'failed': 0}
        response = self.client.post('/api/v1/dashboard/outbox-health/retry/', {'event_ids': [1]}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['processed'], 1)

    @patch('smart_agri.core.api.dashboard.OpsHealthService.attachment_runtime_health_snapshot')
    def test_attachment_runtime_health_endpoint(self, snapshot_mock):
        snapshot_mock.return_value = {'severity': 'critical', 'quarantined': 2}
        response = self.client.get('/api/v1/dashboard/attachment-runtime-health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['quarantined'], 2)

    @patch('smart_agri.core.api.dashboard.OpsHealthService.attachment_runtime_detail_snapshot')
    def test_attachment_runtime_health_detail_endpoint(self, snapshot_mock):
        snapshot_mock.return_value = {'severity': 'critical', 'detail_rows': [{'id': 1}], 'filtered_total': 1}
        response = self.client.get(f'/api/v1/dashboard/attachment-runtime-health/detail/?farm_id={self.farm.id}&limit=10')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['filtered_total'], 1)

    @patch('smart_agri.core.api.dashboard.OpsRemediationService.rescan_attachments')
    def test_attachment_runtime_health_rescan_endpoint(self, rescan_mock):
        rescan_mock.return_value = {'action_id': 'ops-2', 'status': 'completed', 'processed': 1, 'skipped': 0, 'failed': 0}
        response = self.client.post('/api/v1/dashboard/attachment-runtime-health/rescan/', {'attachment_ids': [1]}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['processed'], 1)

    @patch('smart_agri.core.api.dashboard.OpsAlertService.alerts_snapshot')
    def test_ops_alerts_endpoint(self, alerts_mock):
        alerts_mock.return_value = {
            'count': 1,
            'items': [{'fingerprint': 'approval_runtime_attention:farm:1:approval_overdue'}],
            'summary': {'by_kind': {'approval_runtime_attention': 1}},
        }
        response = self.client.get(f'/api/v1/dashboard/ops-alerts/?farm_id={self.farm.id}&limit=10')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        alerts_mock.assert_called_once()

    @patch('smart_agri.core.api.dashboard.OpsAlertService.acknowledge_alert')
    def test_acknowledge_ops_alert_endpoint(self, acknowledge_mock):
        acknowledge_mock.return_value = {
            'fingerprint': 'approval_runtime_attention:farm:1:approval_overdue',
            'status': 'acknowledged',
        }
        response = self.client.post(
            '/api/v1/dashboard/ops-alerts/acknowledge/',
            {'fingerprint': 'approval_runtime_attention:farm:1:approval_overdue'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'acknowledged')

    @patch('smart_agri.core.api.dashboard.OpsAlertService.snooze_alert')
    def test_snooze_ops_alert_endpoint(self, snooze_mock):
        snooze_mock.return_value = {
            'fingerprint': 'approval_runtime_attention:farm:1:approval_overdue',
            'status': 'snoozed',
            'snooze_until': '2026-03-28T18:00:00Z',
        }
        response = self.client.post(
            '/api/v1/dashboard/ops-alerts/snooze/',
            {'fingerprint': 'approval_runtime_attention:farm:1:approval_overdue', 'hours': 4},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'snoozed')

    @patch('smart_agri.core.api.dashboard.OpsAlertService.outbox_trace')
    def test_outbox_health_trace_endpoint(self, trace_mock):
        trace_mock.return_value = {
            'trace_kind': 'outbox',
            'event': {'id': 1},
            'timeline': [{'id': 1}],
        }
        response = self.client.get('/api/v1/dashboard/outbox-health/trace/?event_id=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['trace_kind'], 'outbox')

    @patch('smart_agri.core.api.dashboard.OpsAlertService.attachment_trace')
    def test_attachment_runtime_health_trace_endpoint(self, trace_mock):
        trace_mock.return_value = {
            'trace_kind': 'attachment',
            'attachment': {'id': 1},
            'lifecycle_events': [],
        }
        response = self.client.get('/api/v1/dashboard/attachment-runtime-health/trace/?attachment_id=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['trace_kind'], 'attachment')

    @patch('smart_agri.core.api.dashboard.OpsAlertService.offline_ops_snapshot')
    def test_offline_ops_endpoint(self, offline_mock):
        offline_mock.return_value = {
            'sync_conflict_dlq_pending': 2,
            'offline_sync_quarantine_pending': 1,
            'pending_mode_switch_quarantines': 1,
            'farms': [],
        }
        response = self.client.get(f'/api/v1/dashboard/offline-ops/?farm_id={self.farm.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['sync_conflict_dlq_pending'], 2)
