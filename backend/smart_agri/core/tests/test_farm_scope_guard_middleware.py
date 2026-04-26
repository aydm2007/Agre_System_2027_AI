from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from smart_agri.core.middleware.farm_scope_guard_middleware import FarmScopeGuardMiddleware


class _User:
    is_authenticated = True
    is_superuser = False


class FarmScopeGuardMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(ROOT_URLCONF='smart_agri.urls')
    def test_sets_response_scope_header_when_provided(self):
        middleware = FarmScopeGuardMiddleware(lambda request: HttpResponse('ok'))
        request = self.factory.post('/api/anything/', HTTP_X_FARM_ID='42')
        request.user = _User()
        response = middleware(request)
        self.assertEqual(response['X-Farm-Scope'], '42')

    def test_blocks_mutating_request_without_scope_when_enabled(self):
        import os
        os.environ['STRICT_FARM_SCOPE_HEADERS'] = 'true'
        try:
            middleware = FarmScopeGuardMiddleware(lambda request: HttpResponse('ok'))
            request = self.factory.post('/api/anything/')
            request.user = _User()
            response = middleware(request)
            self.assertEqual(response.status_code, 400)
        finally:
            os.environ['STRICT_FARM_SCOPE_HEADERS'] = 'false'
