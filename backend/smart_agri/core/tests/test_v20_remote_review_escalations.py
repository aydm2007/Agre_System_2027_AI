from django.contrib.auth import get_user_model
from django.test import TestCase

from smart_agri.core.models import Farm, FarmSettings, RemoteReviewEscalation
from smart_agri.core.services.remote_review_service import RemoteReviewService


class RemoteReviewEscalationTests(TestCase):
    def test_record_review_resolves_open_escalations(self):
        user = get_user_model().objects.create(username="sector_reviewer")
        farm = Farm.objects.create(name="Test Farm")
        settings_obj = FarmSettings.objects.create(farm=farm, remote_site=True, weekly_remote_review_required=True)
        RemoteReviewService._open_escalation(farm, RemoteReviewEscalation.LEVEL_DUE, 'weekly_remote_review_due')
        RemoteReviewService.record_review(farm=farm, reviewer=user, notes='ok')
        self.assertFalse(RemoteReviewEscalation.objects.filter(farm=farm, resolved_at__isnull=True).exists())
