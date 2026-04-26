from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(ROOT_URLCONF='smart_agri.urls')
class ObservabilityEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_livez_returns_ok(self):
        response = self.client.get('/api/health/live/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_readyz_returns_probe_payload(self):
        response = self.client.get('/api/health/ready/')
        self.assertIn(response.status_code, (200, 503))
        payload = response.json()
        self.assertIn('database', payload)
        self.assertIn('cache', payload)

    def test_metrics_summary_returns_observability_flags(self):
        response = self.client.get('/api/health/metrics-summary/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('observability', payload)
        self.assertIn('cache_backend', payload['observability'])
