from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from smart_agri.core.models.log import AuditLog
from smart_agri.finance.models import FinancialLedger


class Phase7AuditAppendOnlyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="phase7_user")

    def test_auditlog_is_append_only(self):
        entry = AuditLog.objects.create(
            actor=self.user,
            action="create",
            model="Employee",
            object_id="999",
            new_payload={"reason": "test"},
        )

        entry.payload = {"reason": "mutated"}
        with self.assertRaises(ValidationError):
            entry.save()

        with self.assertRaises(ValidationError):
            entry.delete()

    def test_financial_ledger_create_writes_sensitive_audit(self):
        ledger = FinancialLedger.objects.create(
            account_code=FinancialLedger.ACCOUNT_OVERHEAD,
            debit=10,
            credit=0,
            description="phase7 ledger test",
            created_by=self.user,
            currency="YER",
        )

        audit = AuditLog.objects.filter(
            action="create_sensitive",
            model="FinancialLedger",
            object_id=str(ledger.pk),
        ).first()

        self.assertIsNotNone(audit)
        self.assertEqual(audit.payload.get("reason"), "phase7 ledger test")
        self.assertIn("new_value", audit.payload)
