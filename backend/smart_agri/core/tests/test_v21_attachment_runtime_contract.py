from django.test import TestCase

from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


class AttachmentRuntimeContractTests(TestCase):
    def test_runtime_summary_contains_v21_contract_fields(self):
        payload = AttachmentPolicyService.security_runtime_summary()
        self.assertIn('cdr_enabled', payload)
        self.assertIn('clamd_configured', payload)
        self.assertIn('objectstore_enabled', payload)
