from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


class _DummyFile:
    def __init__(self, name, content_type='application/pdf', payload=b'%PDF-1.4 test'):
        self.name = name
        self.content_type = content_type
        self._payload = payload
        self.size = len(payload)
        self._pos = 0

    def tell(self):
        return self._pos

    def seek(self, pos):
        self._pos = pos

    def read(self, size=-1):
        if size < 0:
            size = len(self._payload) - self._pos
        chunk = self._payload[self._pos:self._pos + size]
        self._pos += len(chunk)
        return chunk


class AttachmentFilenameGuardTests(SimpleTestCase):
    def test_rejects_hidden_executable_suffix(self):
        file_obj = _DummyFile('invoice.php.pdf')
        with self.assertRaises(ValidationError):
            AttachmentPolicyService.validate_upload(farm_settings=None, file_obj=file_obj, evidence_class='transient')

    def test_accepts_safe_filename(self):
        file_obj = _DummyFile('invoice.pdf')
        payload = AttachmentPolicyService.validate_upload(farm_settings=None, file_obj=file_obj, evidence_class='operational')
        self.assertEqual(payload['content_type'], 'application/pdf')
