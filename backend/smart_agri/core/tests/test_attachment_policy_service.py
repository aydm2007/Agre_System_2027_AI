import hashlib

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.log import Attachment
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


class AttachmentPolicyServiceTests(TestCase):
    def _make_attachment(self, file_obj, *, evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL, related_type="invoice"):
        payload = getattr(file_obj, "read", lambda: b"")()
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        checksum = hashlib.sha256(payload).hexdigest()
        return Attachment.objects.create(
            file=file_obj,
            name=getattr(file_obj, "name", "attachment"),
            evidence_class=evidence_class,
            content_type=getattr(file_obj, "content_type", "application/octet-stream") or "application/octet-stream",
            sha256_checksum=checksum,
            size=getattr(file_obj, "size", len(payload)) or len(payload),
            uploaded_by=self.user,
            farm=self.farm,
            related_document_type=related_type,
            filename_original=getattr(file_obj, "name", "attachment"),
            mime_type_detected=getattr(file_obj, "content_type", "application/octet-stream") or "application/octet-stream",
            content_hash=checksum,
            size_bytes=getattr(file_obj, "size", len(payload)) or len(payload),
        )

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="u1", password="pw")
        self.farm = Farm.objects.create(name="Farm A", slug="farm-a", region="Tehama")
        self.settings = FarmSettings.objects.create(farm=self.farm)

    def test_validate_upload_accepts_pdf_signature(self):
        file_obj = SimpleUploadedFile("invoice.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        policy = AttachmentPolicyService.validate_upload(
            farm_settings=self.settings,
            file_obj=file_obj,
            evidence_class=Attachment.EVIDENCE_CLASS_TRANSIENT,
        )
        self.assertIsNotNone(policy["expires_at"])
        self.assertEqual(policy["content_type"], "application/pdf")

    def test_validate_upload_rejects_bad_signature(self):
        file_obj = SimpleUploadedFile("image.png", b"not-a-real-png", content_type="image/png")
        with self.assertRaises(Exception):
            AttachmentPolicyService.validate_upload(
                farm_settings=self.settings,
                file_obj=file_obj,
                evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL,
            )

    def test_validate_upload_rejects_hidden_executable_double_extension(self):
        file_obj = SimpleUploadedFile("invoice.exe.pdf", b"%PDF-1.4 safe", content_type="application/pdf")
        with self.assertRaises(Exception):
            AttachmentPolicyService.validate_upload(
                farm_settings=self.settings,
                file_obj=file_obj,
                evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL,
            )

    def test_scan_attachment_quarantines_bad_file(self):
        file_obj = SimpleUploadedFile("invoice.pdf", b"MZ-malicious", content_type="application/pdf")
        attachment = self._make_attachment(file_obj, evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL)
        AttachmentPolicyService.scan_attachment(attachment=attachment)
        self.assertEqual(attachment.malware_scan_status, Attachment.MALWARE_SCAN_QUARANTINED)
        self.assertTrue(attachment.quarantine_reason)
        self.assertTrue(attachment.quarantined_at)

    def test_mark_authoritative_assigns_archive_key(self):
        file_obj = SimpleUploadedFile("invoice.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        attachment = self._make_attachment(file_obj, evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL)
        AttachmentPolicyService.mark_authoritative_after_approval(attachment=attachment, farm_settings=self.settings)
        self.assertTrue(attachment.archive_key)
        self.assertEqual(attachment.archive_backend, "filesystem")

    def test_mark_authoritative_triggers_scan_and_marks_passed(self):
        file_obj = SimpleUploadedFile("invoice.pdf", b"%PDF-1.4 safe", content_type="application/pdf")
        attachment = self._make_attachment(file_obj, evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL)
        AttachmentPolicyService.mark_authoritative_after_approval(attachment=attachment, farm_settings=self.settings)
        self.assertEqual(attachment.malware_scan_status, Attachment.MALWARE_SCAN_PASSED)
        self.assertTrue(attachment.archive_key)
        self.assertTrue(attachment.scanned_at)

    def test_mark_authoritative_rejects_quarantined_file(self):
        file_obj = SimpleUploadedFile("invoice.pdf", b"%PDF-1.4 /OpenAction bad", content_type="application/pdf")
        attachment = self._make_attachment(file_obj, evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL)
        with self.assertRaises(Exception):
            AttachmentPolicyService.mark_authoritative_after_approval(attachment=attachment, farm_settings=self.settings)

    def test_archive_restore_and_legal_hold_leave_forensic_state(self):
        file_obj = SimpleUploadedFile("invoice.pdf", b"%PDF-1.4 safe", content_type="application/pdf")
        attachment = self._make_attachment(file_obj, evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL)
        AttachmentPolicyService.mark_authoritative_after_approval(attachment=attachment, farm_settings=self.settings)
        AttachmentPolicyService.move_to_archive(attachment=attachment)
        attachment.save()
        self.assertEqual(attachment.storage_tier, Attachment.STORAGE_TIER_ARCHIVE)
        self.assertTrue(attachment.archive_key)
        self.assertTrue(attachment.archived_at)

        AttachmentPolicyService.apply_legal_hold(attachment=attachment)
        attachment.save()
        self.assertEqual(attachment.evidence_class, Attachment.EVIDENCE_CLASS_LEGAL_HOLD)
        self.assertIsNone(attachment.expires_at)

        AttachmentPolicyService.restore_from_archive(attachment=attachment)
        attachment.save()
        self.assertEqual(attachment.storage_tier, Attachment.STORAGE_TIER_HOT)
        self.assertTrue(attachment.restored_at)
