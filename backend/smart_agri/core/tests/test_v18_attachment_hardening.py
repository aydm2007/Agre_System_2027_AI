import io
import zipfile

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


class DummyFile(io.BytesIO):
    def __init__(self, data: bytes, name: str, content_type: str):
        super().__init__(data)
        self.name = name
        self.content_type = content_type
        self.size = len(data)

    def open(self, mode='rb'):
        self.seek(0)
        return self


class AttachmentHardeningTests(SimpleTestCase):
    def test_pdf_javascript_marker_blocked(self):
        payload = b'%PDF-1.7\n1 0 obj\n<< /OpenAction << /JavaScript (app.alert(1)) >> >>'
        file_obj = DummyFile(payload, 'evidence.pdf', 'application/pdf')
        with self.assertRaises(ValidationError):
            AttachmentPolicyService._check_heuristics(file_obj=file_obj, extension='pdf', content_type='application/pdf')

    def test_xlsx_macro_payload_blocked(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('[Content_Types].xml', '<Types/>')
            zf.writestr('xl/vbaProject.bin', b'evil')
        file_obj = DummyFile(buf.getvalue(), 'book.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        with self.assertRaises(ValidationError):
            AttachmentPolicyService._check_zip_container(file_obj=file_obj, extension='xlsx')
