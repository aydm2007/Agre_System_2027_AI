from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from smart_agri.core.models import DailyLog, Farm, OfflineSyncQuarantine, SyncConflictDLQ, SyncRecord, Supervisor


class ReconcileOfflineForensicsCommandTests(TestCase):
    def setUp(self):
        self.resolver = User.objects.create_user("offline-admin", password="pass", is_superuser=True)
        self.actor = User.objects.create_user("offline-actor", password="pass")
        self.farm = Farm.objects.create(name="Offline Trial Farm", slug="offline-trial-farm", region="North")
        self.supervisor = Supervisor.objects.create(farm=self.farm, name="Sup", code="SUP-RCF")

    def test_command_resolves_duplicates_and_approves_mode_switch_quarantine(self):
        log = DailyLog.objects.create(
            farm=self.farm,
            supervisor=self.supervisor,
            log_date="2026-04-29",
            status=DailyLog.STATUS_SUBMITTED,
            created_by=self.actor,
            updated_by=self.actor,
            variance_note=" [⚠️ تم حجر هذا السجل بسبب التبديل إلى الوضع الصارم]",
        )
        SyncConflictDLQ.objects.create(
            farm=self.farm,
            actor=self.actor,
            conflict_type="STALE_VERSION",
            conflict_reason="older duplicate",
            endpoint="/api/v1/offline/daily-log-replay/atomic/",
            http_method="POST",
            request_payload={"payload_uuid": "payload-1", "draft_uuid": "draft-1"},
            idempotency_key="dlq-1",
            status="PENDING",
        )
        keeper = SyncConflictDLQ.objects.create(
            farm=self.farm,
            actor=self.actor,
            conflict_type="STALE_VERSION",
            conflict_reason="newer duplicate",
            endpoint="/api/v1/offline/daily-log-replay/atomic/",
            http_method="POST",
            request_payload={"payload_uuid": "payload-1", "draft_uuid": "draft-1"},
            idempotency_key="dlq-2",
            status="PENDING",
        )
        SyncRecord.objects.create(
            user=self.actor,
            farm=self.farm,
            category=SyncRecord.CATEGORY_DAILY_LOG,
            reference="payload-1",
            status=SyncRecord.STATUS_SUCCESS,
        )
        quarantine = OfflineSyncQuarantine.objects.create(
            farm=self.farm,
            submitted_by=self.actor,
            variance_type="MODE_SWITCH_QUARANTINE",
            device_timestamp=log.created_at,
            original_payload={"daily_log_id": log.id},
            idempotency_key="mode-switch-quarantine-log-test",
            status="PENDING_REVIEW",
        )

        call_command(
            "reconcile_offline_forensics",
            "--farm-id",
            str(self.farm.id),
            "--resolver-username",
            self.resolver.username,
            "--close-legacy-pending",
            "--approve-mode-switch-quarantines",
        )

        keeper.refresh_from_db()
        log.refresh_from_db()
        quarantine.refresh_from_db()

        self.assertIn(
            SyncConflictDLQ.objects.get(idempotency_key="dlq-1").status,
            {"REPLAYED", "RESOLVED"},
        )
        self.assertIn(keeper.status, {"REPLAYED", "RESOLVED"})
        self.assertEqual(quarantine.status, "APPROVED_AND_POSTED")
        self.assertNotIn("تم حجر هذا السجل", log.variance_note or "")
