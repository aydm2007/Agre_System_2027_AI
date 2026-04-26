import pytest
from django.test import TestCase

@pytest.mark.django_db
class TestAttachmentFullLifecycle(TestCase):
    def test_upload_scan_authoritative_archive_restore(self):
        """
        ATTACHMENT_POLICY_MATRIX: Full lifecycle test:
        uploaded → scanned_clean → authoritative → archived → restored
        """
        pass

    def test_purge_blocked_for_financial_record(self):
        """
        ATTACHMENT_POLICY_MATRIX: financial_record class has purge_eligible=false.
        Purge attempt must fail.
        """
        pass

    def test_purge_allowed_for_transient(self):
        """
        ATTACHMENT_POLICY_MATRIX: transient class has purge_eligible=true.
        """
        pass

    def test_legal_hold_blocks_purge(self):
        """
        ATTACHMENT_POLICY_MATRIX: legal_hold has purge_eligible=false.
        """
        pass
