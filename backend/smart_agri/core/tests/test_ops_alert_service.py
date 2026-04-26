from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from smart_agri.core.models import Farm, OfflineSyncQuarantine, OpsAlertReceipt, SyncConflictDLQ
from smart_agri.core.services.ops_alert_service import OpsAlertService


class OpsAlertServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="ops-observer",
            password="pass1234",
            email="ops-observer@example.com",
        )
        self.farm = Farm.objects.create(name="Observability Farm")

    @patch("smart_agri.core.services.ops_alert_service.OpsHealthService.release_health_detail_snapshot")
    @patch("smart_agri.core.services.ops_alert_service.OpsHealthService.integration_outbox_detail_snapshot")
    @patch("smart_agri.core.services.ops_alert_service.OpsHealthService.attachment_runtime_detail_snapshot")
    @patch("smart_agri.core.services.ops_alert_service.ApprovalGovernanceService.attention_feed")
    def test_alerts_snapshot_dedupes_by_fingerprint(
        self,
        attention_feed_mock,
        attachment_detail_mock,
        outbox_detail_mock,
        release_detail_mock,
    ):
        attention_feed_mock.return_value = {
            "items": [
                {
                    "kind": "approval_overdue",
                    "severity": "attention",
                    "farm_id": self.farm.id,
                    "request_id": 11,
                    "role": "sector_accountant",
                    "message": "Approval overdue",
                    "attention_bucket": "approval_overdue",
                },
                {
                    "kind": "approval_overdue",
                    "severity": "attention",
                    "farm_id": self.farm.id,
                    "request_id": 11,
                    "role": "sector_accountant",
                    "message": "Approval overdue",
                    "attention_bucket": "approval_overdue",
                },
            ]
        }
        attachment_detail_mock.return_value = {"detail_rows": [], "filtered_total": 0}
        outbox_detail_mock.return_value = {"detail_rows": [], "filtered_total": 0}
        release_detail_mock.return_value = {"detail_rows": []}

        snapshot = OpsAlertService.alerts_snapshot(user=self.user, farm_id=self.farm.id, limit=10)

        self.assertEqual(snapshot["count"], 1)
        self.assertEqual(snapshot["items"][0]["fingerprint"], "approval_runtime_attention:approval_request:11:approval_overdue")

    def test_acknowledge_and_snooze_persist_operator_state(self):
        acknowledged = OpsAlertService.acknowledge_alert(
            user=self.user,
            fingerprint="approval_runtime_attention:farm:1:approval_overdue",
            note="handled",
            request_id="req-ack",
            correlation_id="corr-ack",
        )
        self.assertEqual(acknowledged["status"], OpsAlertReceipt.STATUS_ACKNOWLEDGED)

        snoozed = OpsAlertService.snooze_alert(
            user=self.user,
            fingerprint="attachment_runtime_attention:farm:1:attachment_scan_blocked",
            hours=4,
            note="wait for next rescan window",
            request_id="req-snooze",
            correlation_id="corr-snooze",
        )
        self.assertEqual(snoozed["status"], OpsAlertReceipt.STATUS_SNOOZED)
        receipt = OpsAlertReceipt.objects.get(
            actor=self.user,
            fingerprint="attachment_runtime_attention:farm:1:attachment_scan_blocked",
        )
        self.assertGreater(receipt.snooze_until, timezone.now() + timedelta(hours=3, minutes=50))

    @patch("smart_agri.core.services.ops_alert_service.OpsHealthService.release_health_detail_snapshot")
    @patch("smart_agri.core.services.ops_alert_service.OpsHealthService.integration_outbox_detail_snapshot")
    @patch("smart_agri.core.services.ops_alert_service.OpsHealthService.attachment_runtime_detail_snapshot")
    @patch("smart_agri.core.services.ops_alert_service.ApprovalGovernanceService.attention_feed")
    def test_alerts_snapshot_hides_acknowledged_and_active_snoozes(
        self,
        attention_feed_mock,
        attachment_detail_mock,
        outbox_detail_mock,
        release_detail_mock,
    ):
        attention_feed_mock.return_value = {
            "items": [
                {
                    "kind": "approval_overdue",
                    "severity": "attention",
                    "farm_id": self.farm.id,
                    "request_id": 21,
                    "role": "sector_accountant",
                    "message": "Approval overdue",
                    "attention_bucket": "approval_overdue",
                }
            ]
        }
        attachment_detail_mock.return_value = {
            "detail_rows": [
                {
                    "id": 3,
                    "farm_id": self.farm.id,
                    "farm_name": self.farm.name,
                    "canonical_reason": "attachment_scan_blocked",
                    "quarantined_at": timezone.now().isoformat(),
                }
            ],
            "filtered_total": 1,
        }
        outbox_detail_mock.return_value = {"detail_rows": [], "filtered_total": 0}
        release_detail_mock.return_value = {"detail_rows": []}

        OpsAlertReceipt.objects.create(
            actor=self.user,
            fingerprint="approval_runtime_attention:approval_request:21:approval_overdue",
            status=OpsAlertReceipt.STATUS_ACKNOWLEDGED,
        )
        OpsAlertReceipt.objects.create(
            actor=self.user,
            fingerprint=f"attachment_runtime_attention:farm:{self.farm.id}:attachment_scan_blocked",
            status=OpsAlertReceipt.STATUS_SNOOZED,
            snooze_until=timezone.now() + timedelta(hours=1),
        )

        snapshot = OpsAlertService.alerts_snapshot(user=self.user, farm_id=self.farm.id, limit=10)
        self.assertEqual(snapshot["count"], 0)

        full_snapshot = OpsAlertService.alerts_snapshot(
            user=self.user,
            farm_id=self.farm.id,
            include_acknowledged=True,
            limit=10,
        )
        self.assertEqual(full_snapshot["count"], 2)

    def test_offline_ops_snapshot_counts_conflicts_and_quarantines(self):
        SyncConflictDLQ.objects.create(
            farm=self.farm,
            actor=self.user,
            conflict_type="OTHER",
            conflict_reason="stale device payload",
            endpoint="/api/v1/daily-logs/",
            http_method="POST",
            request_payload={"id": 1},
            status="PENDING",
        )
        OfflineSyncQuarantine.objects.create(
            farm=self.farm,
            submitted_by=self.user,
            variance_type="MODE_SWITCH_RISK",
            device_timestamp=timezone.now() - timedelta(hours=2),
            original_payload={"id": 1},
            idempotency_key="offline-quarantine-1",
            status="PENDING_REVIEW",
        )

        snapshot = OpsAlertService.offline_ops_snapshot(farm_id=self.farm.id)

        self.assertEqual(snapshot["sync_conflict_dlq_pending"], 1)
        self.assertEqual(snapshot["offline_sync_quarantine_pending"], 1)
        self.assertEqual(snapshot["pending_mode_switch_quarantines"], 1)
