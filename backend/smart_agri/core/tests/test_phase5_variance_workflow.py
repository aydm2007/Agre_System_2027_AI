from decimal import Decimal
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase

from smart_agri.core.models import Activity, DailyLog, Farm
from smart_agri.core.services.log_approval_service import LogApprovalService


class Phase5VarianceWorkflowTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username="creator")
        self.supervisor = User.objects.create_user(username="supervisor")
        self.manager = User.objects.create_user(username="manager")
        self.approver = User.objects.create_user(username="approver")

        Group.objects.get_or_create(name="Supervisor")[0].user_set.add(self.supervisor)
        Group.objects.get_or_create(name="Manager")[0].user_set.add(self.manager)

        self.farm = Farm.objects.create(
            name="Phase5 Farm",
            slug="phase5-farm",
            region="Sanaa",
            area=Decimal("100.00"),
        )
        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date=date(2026, 1, 10),
            created_by=self.creator,
            status=DailyLog.STATUS_SUBMITTED,
        )
        Activity.objects.create(
            log=self.log,
            days_spent=Decimal("1.00"),
            cost_total=Decimal("100.00"),
            created_by=self.creator,
        )

    @patch("smart_agri.core.services.log_approval_service.compute_log_variance")
    def test_warning_requires_note_before_approval(self, variance_mock):
        variance_mock.return_value = {
            "status": "WARNING",
            "max_deviation_pct": Decimal("12.00"),
            "details": [],
        }
        with self.assertRaisesMessage(ValidationError, "WARNING variance requires supervisor note"):
            LogApprovalService.approve_log(self.approver, self.log.pk)

    @patch("smart_agri.core.services.log_approval_service.compute_log_variance")
    def test_warning_note_allows_approval(self, variance_mock):
        variance_mock.return_value = {
            "status": "WARNING",
            "max_deviation_pct": Decimal("12.00"),
            "details": [],
        }
        LogApprovalService.note_warning(self.supervisor, self.log.pk, "Reviewed by supervisor.")
        approved_log = LogApprovalService.approve_log(self.approver, self.log.pk)
        self.assertEqual(approved_log.status, DailyLog.STATUS_APPROVED)
        self.assertEqual(approved_log.variance_status, "WARNING")
        self.assertEqual(approved_log.variance_note, "Reviewed by supervisor.")

    @patch("smart_agri.core.services.log_approval_service.compute_log_variance")
    def test_critical_requires_manager_approval(self, variance_mock):
        variance_mock.return_value = {
            "status": "CRITICAL",
            "max_deviation_pct": Decimal("45.00"),
            "details": [],
        }
        with self.assertRaisesMessage(ValidationError, "CRITICAL variance requires manager approval"):
            LogApprovalService.approve_log(self.approver, self.log.pk)

        LogApprovalService.approve_variance(self.manager, self.log.pk, "Approved by manager.")
        approved_log = LogApprovalService.approve_log(self.approver, self.log.pk)
        self.assertEqual(approved_log.status, DailyLog.STATUS_APPROVED)
        self.assertEqual(approved_log.variance_status, "CRITICAL")
        self.assertEqual(approved_log.variance_approved_by_id, self.manager.id)
