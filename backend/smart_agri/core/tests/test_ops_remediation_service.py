from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from unittest.mock import patch

from smart_agri.core.models import Attachment, AuditLog, Farm, IntegrationOutboxEvent
from smart_agri.core.services.ops_remediation_service import OpsRemediationService


class OpsRemediationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="ops-admin", password="pass1234", email="ops@example.com")
        self.farm = Farm.objects.create(name="Ops Farm")

    def test_retry_outbox_events_requeues_dead_letter_and_records_audit(self):
        event = IntegrationOutboxEvent.objects.create(
            event_id="evt-ops-1",
            event_type="daily_log.synced",
            aggregate_type="DailyLog",
            aggregate_id="1",
            destination="events",
            farm=self.farm,
            status=IntegrationOutboxEvent.Status.DEAD_LETTER,
            attempts=10,
            last_error="network timeout",
            metadata={"correlation_id": "corr-1"},
        )

        result = OpsRemediationService.retry_outbox_events(user=self.user, event_ids=[event.id], request_id="req-1", correlation_id="corr-ops-1")

        event.refresh_from_db()
        self.assertEqual(result["processed"], 1)
        self.assertEqual(event.status, IntegrationOutboxEvent.Status.FAILED)
        self.assertTrue(AuditLog.objects.filter(action="OPS_REMEDIATION_RETRY_OUTBOX").exists())

    def test_rescan_attachments_skips_authoritative_evidence(self):
        attachment = Attachment.objects.create(
            file=SimpleUploadedFile("ops.pdf", b"%PDF-1.4\nops", content_type="application/pdf"),
            name="ops.pdf",
            size=9,
            content_type="application/pdf",
            evidence_class=Attachment.EVIDENCE_CLASS_FINANCIAL,
            is_authoritative_evidence=True,
            sha256_checksum="a" * 64,
            uploaded_by=self.user,
            farm=self.farm,
            related_document_type="ops_test",
            attachment_class=Attachment.EVIDENCE_CLASS_FINANCIAL,
            retention_class=Attachment.EVIDENCE_CLASS_FINANCIAL,
            archive_state=Attachment.ARCHIVE_STATE_HOT,
            scan_state=Attachment.MALWARE_SCAN_PENDING,
            quarantine_state=Attachment.QUARANTINE_STATE_NONE,
            filename_original="ops.pdf",
            mime_type_detected="application/pdf",
            size_bytes=9,
            content_hash="a" * 64,
            authoritative_at=self.farm.created_at,
        )

        result = OpsRemediationService.rescan_attachments(user=self.user, attachment_ids=[attachment.id], request_id="req-2", correlation_id="corr-ops-2")

        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["results"]["skipped_rows"][0]["reason"], "authoritative_evidence_locked")

    @patch("smart_agri.core.services.ops_remediation_service.call_command")
    def test_dry_run_governance_maintenance_returns_output_lines(self, call_command_mock):
        def _write_output(*args, **kwargs):
            stdout = kwargs["stdout"]
            stdout.write("running=scan_pending_attachments\n")
            stdout.write("governance_maintenance_cycle=dry_run_completed\n")

        call_command_mock.side_effect = _write_output

        result = OpsRemediationService.dry_run_governance_maintenance(user=self.user, request_id="req-3", correlation_id="corr-ops-3")

        self.assertEqual(result["status"], "completed")
        self.assertIn("governance_maintenance_cycle=dry_run_completed", result["results"]["output_lines"])
