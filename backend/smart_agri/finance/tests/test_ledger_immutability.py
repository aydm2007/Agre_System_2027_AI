"""
[AGRI-GUARDIAN] Test Suite: Ledger Immutability Enforcement
Target: FinancialLedger model + FinancialLedgerViewSet (ReadOnly)
Protocol II: "Rows in core_financialledger are IMMUTABLE.
             Never UPDATE or DELETE. Corrections must be Reversal Transactions."
"""
import pytest
from decimal import Decimal
from django.test import TestCase
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from smart_agri.finance.models import FinancialLedger


@pytest.mark.django_db
class TestLedgerImmutabilityModel(TestCase):
    """
    التحقق من أن نموذج FinancialLedger يرفض أي تحديث أو حذف
    وفقاً لبروتوكول Agri-Guardian II: الثبات المالي.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="auditor_model", password="pass1234")
        self.entry = FinancialLedger.objects.create(
            account_code=FinancialLedger.ACCOUNT_LABOR,
            debit=Decimal("500.0000"),
            credit=Decimal("0.0000"),
            description="Test entry for immutability",
            created_by=self.user,
        )

    def test_clean_rejects_update(self):
        """
        اختبار: clean() يرفض تحديث سجل موجود مع ValidationError.
        """
        self.entry.description = "Tampered description"
        with self.assertRaises(ValidationError):
            self.entry.clean()

    def test_save_rejects_update(self):
        """
        اختبار: save() يرفض تحديث سجل موجود.
        FinancialLedger.save() calls clean() internally.
        """
        self.entry.debit = Decimal("999.0000")
        with self.assertRaises(ValidationError):
            self.entry.save()

    def test_row_hash_generated_on_create(self):
        """
        اختبار: يتم إنشاء row_hash تلقائياً عند الإنشاء.
        """
        self.assertIsNotNone(self.entry.row_hash)
        self.assertTrue(len(self.entry.row_hash) > 0)

    def test_uuid_primary_key(self):
        """
        اختبار: المفتاح الأساسي هو UUID وليس Integer.
        """
        import uuid
        self.assertIsInstance(self.entry.pk, uuid.UUID)


@pytest.mark.django_db
class TestLedgerImmutabilityAPI(TestCase):
    """
    التحقق من أن FinancialLedgerViewSet (ReadOnly) يرفض جميع
    عمليات الكتابة (POST, PUT, PATCH, DELETE) عبر API.
    The API may return 400 (idempotency middleware) or 405 (method not allowed),
    both are valid rejections — the key assertion is NOT 2xx.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="auditor_api",
            email="auditor@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=self.user)
        self.version = getattr(settings, "APP_VERSION", "2.0.0")
        self.entry = FinancialLedger.objects.create(
            account_code=FinancialLedger.ACCOUNT_MATERIAL,
            debit=Decimal("1000.0000"),
            credit=Decimal("0.0000"),
            description="API immutability test",
            created_by=self.user,
        )

    def _assert_rejected(self, response, msg=""):
        """Mutation must be rejected: any 4xx status is acceptable."""
        self.assertGreaterEqual(response.status_code, 400, msg)
        self.assertLess(response.status_code, 500, msg)

    def test_post_rejected(self):
        """
        اختبار: POST على /finance/ledger/ يُرفض.
        """
        response = self.client.post(
            "/api/v1/finance/ledger/",
            {
                "account_code": FinancialLedger.ACCOUNT_LABOR,
                "debit": "100.0000",
                "credit": "0.0000",
                "description": "Illegal insert",
            },
            HTTP_X_APP_VERSION=self.version,
        )
        self._assert_rejected(response, "POST should be rejected on ReadOnly ledger")

    def test_put_rejected(self):
        """
        اختبار: PUT على /finance/ledger/{id}/ يُرفض.
        """
        response = self.client.put(
            f"/api/v1/finance/ledger/{self.entry.pk}/",
            {"description": "Tampered"},
            HTTP_X_APP_VERSION=self.version,
        )
        self._assert_rejected(response, "PUT should be rejected on ReadOnly ledger")

    def test_patch_rejected(self):
        """
        اختبار: PATCH على /finance/ledger/{id}/ يُرفض.
        """
        response = self.client.patch(
            f"/api/v1/finance/ledger/{self.entry.pk}/",
            {"debit": "999.0000"},
            HTTP_X_APP_VERSION=self.version,
        )
        self._assert_rejected(response, "PATCH should be rejected on ReadOnly ledger")

    def test_delete_rejected(self):
        """
        اختبار: DELETE على /finance/ledger/{id}/ يُرفض.
        """
        response = self.client.delete(
            f"/api/v1/finance/ledger/{self.entry.pk}/",
            HTTP_X_APP_VERSION=self.version,
        )
        self._assert_rejected(response, "DELETE should be rejected on ReadOnly ledger")
