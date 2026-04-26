from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from smart_agri.core.middleware.request_observability_middleware import RequestObservabilityMiddleware


class RequestObservabilityMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_generates_request_id_and_timing_headers(self):
        middleware = RequestObservabilityMiddleware(lambda request: HttpResponse('ok'))
        response = middleware(self.factory.get('/health/live/'))
        assert response.status_code == 200
        assert response['X-Request-Id']
        assert response['X-Correlation-Id']
        assert response['X-Response-Time-Ms']

    def test_reuses_incoming_request_id(self):
        middleware = RequestObservabilityMiddleware(lambda request: HttpResponse('ok'))
        response = middleware(self.factory.get('/health/live/', HTTP_X_REQUEST_ID='abc-123'))
        assert response['X-Request-Id'] == 'abc-123'

    def test_uses_idempotency_key_as_correlation_id_when_present(self):
        middleware = RequestObservabilityMiddleware(lambda request: HttpResponse('ok'))
        response = middleware(
            self.factory.post('/api/v1/finance/approval-requests/', HTTP_X_IDEMPOTENCY_KEY='idem-123')
        )
        assert response['X-Correlation-Id'] == 'idem-123'

    def test_skips_policy_lookup_for_multi_farm_scope_queries(self):
        middleware = RequestObservabilityMiddleware(lambda request: HttpResponse('ok'))
        response = middleware(self.factory.get('/api/v1/farms/', {'farm_id': '30,29,31'}))
        assert response.status_code == 200
        assert response['X-Request-Id']
