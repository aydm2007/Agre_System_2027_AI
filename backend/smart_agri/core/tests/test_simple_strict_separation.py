"""
SIMPLE / STRICT Separation Tests
==================================
[AGRI-GUARDIAN AXES 6+15 / AGENTS.md §12,14 / PRD V21 §7 / READINESS_MATRIX §simple_strict_boundary]

Verifies that:
1. SIMPLE mode farms cannot access finance routes (RouteBreachAuditMiddleware blocks + AuditLog emitted)
2. STRICT mode farms CAN access finance routes
3. AuditLog 'ROUTE_BREACH_ATTEMPT' is emitted on SIMPLE breach
4. FarmSettings.mode is the canonical contract (not SystemSettings.strict_erp_mode)
5. SIMPLE remains a technical control surface — no authoring mutation on finance routes
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

User = get_user_model()


class SimpleModeRouteBlockTests(TestCase):
    """
    Tests that financial API routes are blocked in SIMPLE mode.
    [Axis 6 / AGENTS.md §12 / READINESS_MATRIX must_pass: no_strict_route_leakage_in_simple]
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='field_operator',
            password='pass1234',
        )

    def _build_simple_farm_settings(self):
        mock_settings = MagicMock()
        mock_settings.mode = 'SIMPLE'
        return mock_settings

    def _build_strict_farm_settings(self):
        mock_settings = MagicMock()
        mock_settings.mode = 'STRICT'
        return mock_settings

    def test_finance_route_returns_403_in_simple_mode(self):
        """[AXIS 6] /api/v1/finance/ must be blocked in SIMPLE mode."""
        from smart_agri.core.middleware.route_breach_middleware import RouteBreachAuditMiddleware

        def dummy_view(req):
            from django.http import HttpResponse
            return HttpResponse("OK", status=200)

        middleware = RouteBreachAuditMiddleware(dummy_view)
        request = self.factory.get('/api/v1/finance/ledger/', HTTP_X_FARM_ID='1')
        request.user = self.user

        with patch(
            'smart_agri.core.models.settings.FarmSettings'
        ) as mock_fs_class, patch(
            'smart_agri.core.models.log.AuditLog'
        ) as mock_audit:
            mock_fs_class.objects.filter.return_value.first.return_value = (
                self._build_simple_farm_settings()
            )
            mock_fs_class.MODE_STRICT = 'STRICT'
            mock_audit.objects.create = MagicMock()

            response = middleware(request)

        self.assertEqual(response.status_code, 403)

    def test_finance_route_returns_403_emits_audit_log(self):
        """[AXIS 7] AuditLog ROUTE_BREACH_ATTEMPT must be emitted on SIMPLE mode breach."""
        from smart_agri.core.middleware.route_breach_middleware import RouteBreachAuditMiddleware

        def dummy_view(req):
            from django.http import HttpResponse
            return HttpResponse("OK", status=200)

        middleware = RouteBreachAuditMiddleware(dummy_view)
        request = self.factory.get('/api/v1/finance/ledger/', HTTP_X_FARM_ID='1')
        request.user = self.user

        with patch(
            'smart_agri.core.models.settings.FarmSettings'
        ) as mock_fs_class, patch(
            'smart_agri.core.models.log.AuditLog'
        ) as mock_audit:
            mock_fs_class.objects.filter.return_value.first.return_value = (
                self._build_simple_farm_settings()
            )
            mock_fs_class.MODE_STRICT = 'STRICT'
            mock_audit.objects.create = MagicMock()

            middleware(request)

        # Must emit AuditLog on breach
        self.assertTrue(mock_audit.objects.create.called, "AuditLog.create must be called on SIMPLE mode breach")
        call_kwargs = mock_audit.objects.create.call_args[1]
        self.assertEqual(call_kwargs.get('action'), 'ROUTE_BREACH_ATTEMPT')

    def test_finance_route_allowed_in_strict_mode(self):
        """[AXIS 6] /api/v1/finance/ must pass through in STRICT mode."""
        from smart_agri.core.middleware.route_breach_middleware import RouteBreachAuditMiddleware

        def dummy_view(req):
            from django.http import HttpResponse
            return HttpResponse("OK", status=200)

        middleware = RouteBreachAuditMiddleware(dummy_view)
        request = self.factory.get('/api/v1/finance/ledger/', HTTP_X_FARM_ID='1')
        request.user = self.user

        with patch(
            'smart_agri.core.models.settings.FarmSettings'
        ) as mock_fs_class:
            mock_fs_class.objects.filter.return_value.first.return_value = (
                self._build_strict_farm_settings()
            )
            mock_fs_class.MODE_STRICT = 'STRICT'
            response = middleware(request)

        self.assertEqual(response.status_code, 200)

    def test_treasury_route_blocked_in_simple(self):
        """[AXIS 6] /api/v1/treasury/ must be blocked in SIMPLE mode."""
        from smart_agri.core.middleware.route_breach_middleware import RouteBreachAuditMiddleware

        def dummy_view(req):
            from django.http import HttpResponse
            return HttpResponse("OK", status=200)

        middleware = RouteBreachAuditMiddleware(dummy_view)
        request = self.factory.post('/api/v1/treasury/deposit/', data={}, HTTP_X_FARM_ID='1')
        request.user = self.user

        with patch(
            'smart_agri.core.models.settings.FarmSettings'
        ) as mock_fs_class, patch(
            'smart_agri.core.models.log.AuditLog'
        ) as mock_audit:
            mock_fs_class.objects.filter.return_value.first.return_value = (
                self._build_simple_farm_settings()
            )
            mock_fs_class.MODE_STRICT = 'STRICT'
            mock_audit.objects.create = MagicMock()

            response = middleware(request)

        self.assertEqual(response.status_code, 403)

    def test_non_finance_routes_not_blocked_in_simple(self):
        """[AXIS 6] Non-finance routes must not be blocked in SIMPLE mode."""
        from smart_agri.core.middleware.route_breach_middleware import RouteBreachAuditMiddleware

        def dummy_view(req):
            from django.http import HttpResponse
            return HttpResponse("OK", status=200)

        middleware = RouteBreachAuditMiddleware(dummy_view)
        request = self.factory.get('/api/v1/crop-plans/', HTTP_X_FARM_ID='1')
        request.user = self.user

        with patch(
            'smart_agri.core.models.settings.FarmSettings'
        ) as mock_fs_class:
            mock_fs_class.objects.filter.return_value.first.return_value = (
                self._build_simple_farm_settings()
            )
            mock_fs_class.MODE_STRICT = 'STRICT'

            response = middleware(request)

        self.assertEqual(response.status_code, 200,
                         "Operational routes must be accessible in SIMPLE mode")

    def test_response_contains_arabic_detail(self):
        """[UI/RTL] Breach response must include Arabic detail message."""
        from smart_agri.core.middleware.route_breach_middleware import RouteBreachAuditMiddleware
        import json

        def dummy_view(req):
            from django.http import HttpResponse
            return HttpResponse("OK", status=200)

        middleware = RouteBreachAuditMiddleware(dummy_view)
        request = self.factory.get('/api/v1/finance/ledger/', HTTP_X_FARM_ID='1')
        request.user = self.user

        with patch(
            'smart_agri.core.models.settings.FarmSettings'
        ) as mock_fs_class, patch(
            'smart_agri.core.models.log.AuditLog'
        ) as mock_audit:
            mock_fs_class.objects.filter.return_value.first.return_value = (
                self._build_simple_farm_settings()
            )
            mock_fs_class.MODE_STRICT = 'STRICT'
            mock_audit.objects.create = MagicMock()

            response = middleware(request)

        body = json.loads(response.content)
        self.assertIn('detail', body)
        self.assertEqual(body.get('code'), 'ROUTE_BREACH_SIMPLE_MODE')

    def test_farm_settings_mode_is_canonical_contract(self):
        """[PRD V21 §7] FarmSettings.mode (not SystemSettings) governs mode contract."""
        from smart_agri.core.models.settings import FarmSettings
        # FarmSettings must define MODE_SIMPLE and MODE_STRICT
        self.assertTrue(hasattr(FarmSettings, 'MODE_SIMPLE'),
                        "FarmSettings must define MODE_SIMPLE")
        self.assertTrue(hasattr(FarmSettings, 'MODE_STRICT'),
                        "FarmSettings must define MODE_STRICT")
        self.assertNotEqual(FarmSettings.MODE_SIMPLE, FarmSettings.MODE_STRICT,
                            "SIMPLE and STRICT modes must be distinct values")

    def test_mode_policy_service_uses_farm_settings(self):
        """[AGENTS.md §119] mode_policy_service.resolve_farm_settings uses FarmSettings."""
        from smart_agri.core.services.mode_policy_service import resolve_farm_settings, build_fallback_settings
        from smart_agri.core.models.settings import FarmSettings

        # Fallback settings must default to SIMPLE
        fallback = build_fallback_settings()
        self.assertEqual(fallback.mode, FarmSettings.MODE_SIMPLE,
                         "Fallback mode must be SIMPLE (safe default)")


class StrictModePermissionClassifierTests(TestCase):
    """
    [AGENTS.md §12 / strict_mode_permissions.py]
    Validates permission classification uses FarmSettings.mode contract.
    """

    def test_financial_ledger_is_strict_permission(self):
        """view_financialledger must be a strict-mode-only permission."""
        from smart_agri.core.strict_mode_permissions import is_strict_permission
        self.assertTrue(is_strict_permission('view_financialledger'))

    def test_fiscal_period_is_strict_permission(self):
        """change_fiscalperiod must be strict-mode-only."""
        from smart_agri.core.strict_mode_permissions import is_strict_permission
        self.assertTrue(is_strict_permission('change_fiscalperiod'))

    def test_approval_request_is_strict_permission(self):
        """view_approvalrequest must be strict-mode-only."""
        from smart_agri.core.strict_mode_permissions import is_strict_permission
        self.assertTrue(is_strict_permission('view_approvalrequest'))

    def test_crop_plan_is_not_strict_permission(self):
        """Operational perms like view_cropplan must NOT be strict-only."""
        from smart_agri.core.strict_mode_permissions import is_strict_permission
        # crop plans are operational — accessible in both modes
        self.assertFalse(is_strict_permission('view_cropplan'))

    def test_classify_permissions_splits_correctly(self):
        """classify_permissions must correctly split strict vs general perms."""
        from smart_agri.core.strict_mode_permissions import classify_permissions
        codenames = ['view_financialledger', 'view_cropplan', 'change_fiscalperiod']
        strict_set, general_set = classify_permissions(codenames)
        self.assertIn('view_financialledger', strict_set)
        self.assertIn('change_fiscalperiod', strict_set)
        self.assertIn('view_cropplan', general_set)
        self.assertNotIn('view_cropplan', strict_set)
