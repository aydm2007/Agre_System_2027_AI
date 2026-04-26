from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.core.models.report import AsyncReportRequest


class ReportingJobRescueTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username='report-rescue-admin',
            password='pass1234',
            email='report-rescue@example.com',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_status_poll_rescues_stalled_job_once(self):
        job = AsyncReportRequest.objects.create(
            created_by=self.user,
            report_type=AsyncReportRequest.REPORT_ADVANCED,
            params={'farm_id': 31},
            requested_at=timezone.now() - timedelta(seconds=30),
        )

        with patch(
            'smart_agri.core.services.reporting_orchestration_service.ReportingOrchestrationService._run_inline_generation_async'
        ) as mock_runner:
            first_response = self.client.get(f'/api/v1/advanced-report/requests/{job.id}/')
            second_response = self.client.get(f'/api/v1/advanced-report/requests/{job.id}/')

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertTrue(first_response.json()['stalled'])
        self.assertEqual(first_response.json()['status'], AsyncReportRequest.STATUS_PENDING)
        self.assertEqual(mock_runner.call_count, 1)

        job.refresh_from_db()
        self.assertIn('rescue', job.metadata)
        self.assertTrue(job.metadata['rescue'].get('attempted_at'))

    def test_completed_job_is_not_rescued(self):
        job = AsyncReportRequest.objects.create(
            created_by=self.user,
            report_type=AsyncReportRequest.REPORT_ADVANCED,
            params={'farm_id': 31},
            status=AsyncReportRequest.STATUS_COMPLETED,
            result_url='/media/reports/existing.json',
            completed_at=timezone.now(),
            requested_at=timezone.now() - timedelta(seconds=30),
        )

        with patch(
            'smart_agri.core.services.reporting_orchestration_service.ReportingOrchestrationService._run_inline_generation_async'
        ) as mock_runner:
            response = self.client.get(f'/api/v1/advanced-report/requests/{job.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['stalled'])
        self.assertEqual(mock_runner.call_count, 0)
