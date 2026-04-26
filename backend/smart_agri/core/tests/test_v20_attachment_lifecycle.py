from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
import hashlib
from smart_agri.core.models.farm import Farm

from smart_agri.core.models import Attachment, AttachmentLifecycleEvent
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


class AttachmentLifecycleServiceTests(TestCase):
    def test_apply_and_release_legal_hold_record_events(self):
        user = get_user_model().objects.create_user(username='u2', password='pw')
        farm = Farm.objects.create(name='Farm B', slug='farm-b', region='Tehama')
        file_obj = SimpleUploadedFile('evidence.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        checksum = hashlib.sha256(b'%PDF-1.4 test').hexdigest()
        attachment = Attachment.objects.create(
            file=file_obj,
            name='evidence.pdf',
            evidence_class=Attachment.EVIDENCE_CLASS_FINANCIAL,
            content_type='application/pdf',
            sha256_checksum=checksum,
            size=file_obj.size,
            uploaded_by=user,
            farm=farm,
            related_document_type='audit',
            filename_original='evidence.pdf',
            mime_type_detected='application/pdf',
            content_hash=checksum,
            size_bytes=file_obj.size,
        )
        AttachmentPolicyService.apply_legal_hold(attachment=attachment)
        AttachmentPolicyService.release_legal_hold(attachment=attachment)
        actions = list(AttachmentLifecycleEvent.objects.filter(attachment=attachment).values_list('action', flat=True))
        self.assertIn(AttachmentLifecycleEvent.ACTION_LEGAL_HOLD_APPLIED, actions)
        self.assertIn(AttachmentLifecycleEvent.ACTION_LEGAL_HOLD_RELEASED, actions)
