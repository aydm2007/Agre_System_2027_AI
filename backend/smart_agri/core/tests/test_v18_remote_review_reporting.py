from django.contrib.auth.models import User
from django.test import TestCase

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.remote_review_service import RemoteReviewService


class RemoteReviewReportingTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Remote Farm")
        self.settings = FarmSettings.objects.create(
            farm=self.farm,
            remote_site=True,
            weekly_remote_review_required=True,
        )
        self.user = User.objects.create_user(username="sector-reviewer", password="pass")

    def test_due_report_contains_remote_farm(self):
        payload = RemoteReviewService.report_due_reviews()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['farm_id'], self.farm.id)
        self.assertTrue(payload[0]['is_overdue'])

    def test_record_review_clears_due_status(self):
        RemoteReviewService.record_review(farm=self.farm, reviewer=self.user, notes='weekly review')
        payload = RemoteReviewService.report_due_reviews()
        self.assertEqual(payload, [])
