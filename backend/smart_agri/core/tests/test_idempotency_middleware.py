"""
Tests for IdempotencyMiddleware
================================
[AGRI-GUARDIAN Axis 2 / AGENTS.md Rule#4]

Validates that financial mutation paths enforce X-Idempotency-Key
through the middleware layer.
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory, override_settings
from django.http import JsonResponse

from smart_agri.core.middleware.idempotency_middleware import IdempotencyMiddleware


def _make_ok_response(request):
    return JsonResponse({"ok": True}, status=200)


class TestIdempotencyMiddlewareKeyEnforcement(TestCase):
    """Validates that financial POST/PATCH without key → 400."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = IdempotencyMiddleware(_make_ok_response)

    def test_get_passes_without_key(self):
        """GET requests do not require idempotency key."""
        request = self.factory.get("/api/v1/finance/ledger/")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_post_to_finance_without_key_returns_400(self):
        """POST to financial path without X-Idempotency-Key → 400."""
        request = self.factory.post(
            "/api/v1/finance/ledger/",
            data=json.dumps({"amount": "100"}),
            content_type="application/json",
        )
        user = MagicMock()
        user.is_authenticated = True
        user.username = "test_user"
        request.user = user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data["code"], "IDEMPOTENCY_KEY_REQUIRED")

    def test_post_to_treasury_without_key_returns_400(self):
        """POST to treasury path without key → 400."""
        request = self.factory.post("/api/v1/treasury/deposit/")
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)

    def test_post_to_petty_cash_without_key_returns_400(self):
        """POST to petty-cash path without key → 400."""
        request = self.factory.post("/api/v1/petty-cash/request/")
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)

    def test_post_to_non_financial_path_passes(self):
        """POST to non-financial path passes without key."""
        request = self.factory.post(
            "/api/v1/crops/",
            data=json.dumps({"name": "test"}),
            content_type="application/json",
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_post_to_auth_path_passes(self):
        """POST to safe prefix passes without key."""
        request = self.factory.post("/api/auth/login/")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_post_to_financial_dashboard_passes(self):
        """GET-like dashboard suffix on financial path passes."""
        request = self.factory.post("/api/v1/finance/dashboard/")
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_patch_to_supplier_settlement_without_key_returns_400(self):
        """PATCH to supplier-settlement without key → 400."""
        request = self.factory.patch("/api/v1/supplier-settlement/42/")
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)

    def test_delete_to_fiscal_without_key_returns_400(self):
        """DELETE to fiscal path without key → 400."""
        request = self.factory.delete("/api/v1/fiscal/periods/1/")
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)

    def test_post_with_key_passes_to_downstream(self):
        """POST with X-Idempotency-Key yields a downstream call."""
        request = self.factory.post(
            "/api/v1/finance/ledger/",
            data=json.dumps({"amount": "100"}),
            content_type="application/json",
            HTTP_X_IDEMPOTENCY_KEY="test-key-001",
        )
        # Without user authentication, should pass through
        request.user = MagicMock()
        request.user.is_authenticated = False
        response = self.middleware(request)
        # Unauthenticated → goes to downstream, which returns 200
        self.assertEqual(response.status_code, 200)


class TestIdempotencyMiddlewareCoverage(TestCase):
    """Validates all financial mutation prefix coverage."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = IdempotencyMiddleware(_make_ok_response)

    def _post_as_authed_user(self, path):
        request = self.factory.post(path)
        user = MagicMock()
        user.is_authenticated = True
        request.user = user
        return self.middleware(request)

    def test_fuel_reconciliation_requires_key(self):
        response = self._post_as_authed_user("/api/v1/fuel-reconciliation/submit/")
        self.assertEqual(response.status_code, 400)

    def test_fixed_assets_requires_key(self):
        response = self._post_as_authed_user("/api/v1/fixed-assets/capitalize/")
        self.assertEqual(response.status_code, 400)

    def test_advances_requires_key(self):
        response = self._post_as_authed_user("/api/v1/advances/disburse/")
        self.assertEqual(response.status_code, 400)

    def test_approval_requires_key(self):
        response = self._post_as_authed_user("/api/v1/approval/requests/")
        self.assertEqual(response.status_code, 400)

    def test_expenses_requires_key(self):
        response = self._post_as_authed_user("/api/v1/expenses/create/")
        self.assertEqual(response.status_code, 400)

    def test_ledger_requires_key(self):
        response = self._post_as_authed_user("/api/v1/ledger/post/")
        self.assertEqual(response.status_code, 400)
