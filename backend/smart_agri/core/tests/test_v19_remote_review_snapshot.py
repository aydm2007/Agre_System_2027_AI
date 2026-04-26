from django.test import TestCase

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.remote_review_service import RemoteReviewService


class RemoteReviewSnapshotTests(TestCase):
    def test_report_due_reviews_exposes_owner_role_and_status(self):
        farm = Farm.objects.create(name='Alpha', code='A1', tier='SMALL')
        FarmSettings.objects.create(farm=farm, remote_site=True, weekly_remote_review_required=True)
        payload = RemoteReviewService.report_due_reviews()
        self.assertEqual(payload[0]['review_status'], 'OVERDUE')
        self.assertTrue(payload[0]['block_strict_finance'])
        self.assertEqual(payload[0]['sector_owner_role'], 'مدير القطاع')
