from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from smart_agri.core.models import Asset, Attachment, AttachmentLifecycleEvent, AuditLog, Farm, IntegrationOutboxEvent
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService
from smart_agri.finance.models import ApprovalRequest


@override_settings(AUTO_CREATE_FISCAL_PERIOD=True)
class SeedRuntimeGovernanceEvidenceCommandTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.archive_dir = TemporaryDirectory()
        self.quarantine_dir = TemporaryDirectory()
        self.sanitized_dir = TemporaryDirectory()

        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_dir.cleanup)
        self.addCleanup(self.archive_dir.cleanup)
        self.addCleanup(self.quarantine_dir.cleanup)
        self.addCleanup(self.sanitized_dir.cleanup)

        self.archive_patch = patch.object(AttachmentPolicyService, "ARCHIVE_ROOT", Path(self.archive_dir.name))
        self.quarantine_patch = patch.object(AttachmentPolicyService, "QUARANTINE_ROOT", Path(self.quarantine_dir.name))
        self.sanitized_patch = patch.object(AttachmentPolicyService, "SANITIZED_ROOT", Path(self.sanitized_dir.name))
        self.objectstore_patch = patch.object(AttachmentPolicyService, "OBJECTSTORE_ENABLED", False)
        self.cdr_patch = patch.object(AttachmentPolicyService, "CDR_COMMAND", "")
        self.clamd_patch = patch.object(AttachmentPolicyService, "CLAMD_SCAN_COMMAND", "")
        for patcher in (
            self.archive_patch,
            self.quarantine_patch,
            self.sanitized_patch,
            self.objectstore_patch,
            self.cdr_patch,
            self.clamd_patch,
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _snapshot(self):
        strict_farm = Farm.objects.get(slug="strict-evidence-farm")
        asset = Asset.objects.get(farm=strict_farm, code="EVID-SOLAR-1", deleted_at__isnull=True)

        clean = Attachment.objects.get(farm=strict_farm, filename_original="seed_clean_evidence.pdf")
        quarantine = Attachment.objects.get(farm=strict_farm, filename_original="seed_suspicious_evidence.pdf")
        transient = Attachment.objects.get(farm=strict_farm, filename_original="seed_draft.csv")

        approval_counts = {
            action: ApprovalRequest.objects.filter(farm=strict_farm, action=action).count()
            for action in (
                "contract_payment_posting",
                "petty_cash_settlement",
                "supplier_settlement",
                "fuel_reconciliation",
                "fixed_asset_posting",
            )
        }

        return {
            "farm_id": strict_farm.id,
            "asset_id": asset.id,
            "fixed_asset_audits": AuditLog.objects.filter(
                action="FIXED_ASSET_CAPITALIZE",
                object_id=str(asset.pk),
            ).count(),
            "fuel_audits": AuditLog.objects.filter(action="FUEL_RECONCILIATION_POST").count(),
            "approval_counts": approval_counts,
            "attachment_counts": {
                name: Attachment.objects.filter(farm=strict_farm, filename_original=name).count()
                for name in (
                    "seed_clean_evidence.pdf",
                    "seed_suspicious_evidence.pdf",
                    "seed_draft.csv",
                )
            },
            "outbox_counts": {
                event_id: IntegrationOutboxEvent.objects.filter(event_id=event_id).count()
                for event_id in (
                    "seed-readiness-success",
                    "seed-readiness-dispatched",
                    "seed-readiness-retry",
                    "seed-readiness-dead-letter",
                )
            },
            "attachments": {
                "clean": clean,
                "quarantine": quarantine,
                "transient": transient,
            },
        }

    def test_seed_runtime_governance_evidence_is_rerunnable_without_duplicate_governed_rows(self):
        call_command("seed_runtime_governance_evidence")
        first = self._snapshot()

        self.assertEqual(first["fixed_asset_audits"], 1)
        self.assertEqual(first["fuel_audits"], 1)
        self.assertEqual(first["approval_counts"]["contract_payment_posting"], 1)
        self.assertEqual(first["approval_counts"]["petty_cash_settlement"], 1)
        self.assertEqual(first["approval_counts"]["supplier_settlement"], 1)
        self.assertEqual(first["approval_counts"]["fuel_reconciliation"], 1)
        self.assertEqual(first["approval_counts"]["fixed_asset_posting"], 1)
        self.assertEqual(first["attachment_counts"]["seed_clean_evidence.pdf"], 1)
        self.assertEqual(first["attachment_counts"]["seed_suspicious_evidence.pdf"], 1)
        self.assertEqual(first["attachment_counts"]["seed_draft.csv"], 1)
        self.assertEqual(first["outbox_counts"]["seed-readiness-success"], 1)
        self.assertEqual(first["outbox_counts"]["seed-readiness-dispatched"], 1)
        self.assertEqual(first["outbox_counts"]["seed-readiness-retry"], 1)
        self.assertEqual(first["outbox_counts"]["seed-readiness-dead-letter"], 1)

        clean = first["attachments"]["clean"]
        quarantine = first["attachments"]["quarantine"]
        transient = first["attachments"]["transient"]

        self.assertEqual(clean.malware_scan_status, Attachment.MALWARE_SCAN_PASSED)
        self.assertTrue(clean.is_authoritative_evidence)
        self.assertTrue(clean.archive_key)
        self.assertIsNotNone(clean.restored_at)
        self.assertIn(clean.storage_tier, {Attachment.STORAGE_TIER_HOT, Attachment.STORAGE_TIER_ARCHIVE})
        self.assertEqual(quarantine.malware_scan_status, Attachment.MALWARE_SCAN_QUARANTINED)
        self.assertIsNotNone(quarantine.quarantined_at)
        self.assertIsNotNone(transient.deleted_at)
        self.assertTrue(
            AttachmentLifecycleEvent.objects.filter(
                attachment=clean,
                action=AttachmentLifecycleEvent.ACTION_ARCHIVED,
            ).exists()
        )

        with patch(
            "smart_agri.core.management.commands.seed_runtime_governance_evidence.FixedAssetLifecycleService.capitalize_asset",
            wraps=None,
        ) as mocked_capitalize:
            call_command("seed_runtime_governance_evidence")
            self.assertEqual(mocked_capitalize.call_count, 0)

        second = self._snapshot()

        self.assertEqual(second["farm_id"], first["farm_id"])
        self.assertEqual(second["asset_id"], first["asset_id"])
        self.assertEqual(second["fixed_asset_audits"], first["fixed_asset_audits"])
        self.assertEqual(second["fuel_audits"], first["fuel_audits"])
        self.assertEqual(second["approval_counts"], first["approval_counts"])
        self.assertEqual(second["attachment_counts"], first["attachment_counts"])
        self.assertEqual(second["outbox_counts"], first["outbox_counts"])
