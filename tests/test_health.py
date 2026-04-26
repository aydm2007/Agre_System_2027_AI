
from django.test import TestCase
from rest_framework.test import APIClient

class HealthTest(TestCase):
    def test_health(self):
        client = APIClient()
        resp = client.get('/api/health/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/json')
        self.assertEqual(resp.json().get('version'), '2.0')
        self.assertEqual(resp.json().get('status'), 'ok')
