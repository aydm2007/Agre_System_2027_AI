"""
V21 SIMPLE display flag hardening tests
======================================

Display-only compatibility flags in SIMPLE mode must not reopen governed
mutation or STRICT-only authoring paths.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase


User = get_user_model()


class SimpleModeDisplayFlagRouteTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="simple_display_user", password="pw123456")

    def _simple_settings(self, **overrides):
        settings_obj = MagicMock()
        settings_obj.mode = "SIMPLE"
        settings_obj.show_finance_in_simple = False
        settings_obj.show_stock_in_simple = False
        settings_obj.show_employees_in_simple = False
        for key, value in overrides.items():
            setattr(settings_obj, key, value)
        return settings_obj

    def test_show_stock_in_simple_does_not_bypass_governed_mutation_block(self):
        from smart_agri.core.middleware.route_breach_middleware import RouteBreachAuditMiddleware

        def dummy_view(req):
            from django.http import HttpResponse

            return HttpResponse("OK", status=200)

        middleware = RouteBreachAuditMiddleware(dummy_view)
        request = self.factory.post("/api/v1/fixed-assets/capitalize/", data={}, HTTP_X_FARM_ID="1")
        request.user = self.user

        with patch("smart_agri.core.models.settings.FarmSettings") as mock_fs_class, patch(
            "smart_agri.core.models.log.AuditLog"
        ) as mock_audit:
            mock_fs_class.objects.filter.return_value.first.return_value = self._simple_settings(
                show_stock_in_simple=True
            )
            mock_fs_class.MODE_STRICT = "STRICT"
            mock_audit.objects.create = MagicMock()

            response = middleware(request)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(mock_audit.objects.create.called)


class StrictModeRequiredDisplayFlagTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_show_finance_in_simple_does_not_authorize_mutation(self):
        from smart_agri.core.models.settings import FarmSettings
        from smart_agri.core.permissions import StrictModeRequired

        request = self.factory.post("/api/v1/fixed-assets/", data={}, HTTP_X_FARM_ID="9")
        permission = StrictModeRequired()
        mocked_settings = MagicMock(
            mode=FarmSettings.MODE_SIMPLE,
            show_finance_in_simple=True,
            show_employees_in_simple=False,
        )

        with patch("smart_agri.core.permissions.FarmSettings.objects.get", return_value=mocked_settings):
            self.assertFalse(permission.has_permission(request, view=None))

    def test_show_employees_in_simple_does_not_authorize_mutation(self):
        from smart_agri.core.models.settings import FarmSettings
        from smart_agri.core.permissions import StrictModeRequired

        request = self.factory.post("/api/v1/fixed-assets/", data={}, HTTP_X_FARM_ID="9")
        permission = StrictModeRequired()
        mocked_settings = MagicMock(
            mode=FarmSettings.MODE_SIMPLE,
            show_finance_in_simple=False,
            show_employees_in_simple=True,
        )

        with patch("smart_agri.core.permissions.FarmSettings.objects.get", return_value=mocked_settings):
            self.assertFalse(permission.has_permission(request, view=None))
