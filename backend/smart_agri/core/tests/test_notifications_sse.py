import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class NotificationsSSEAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sse_user', password='password')
        self.client = APIClient()

    def test_notifications_stream_requires_authentication(self):
        response = self.client.get('/api/v1/notifications/stream/')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['code'], 'AUTHENTICATION_REQUIRED')

    def test_notifications_stream_accepts_access_token_query_param(self):
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)

        response = self.client.get(
            f'/api/v1/notifications/stream/?access_token={access_token}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

        first_event = next(iter(response.streaming_content)).decode('utf-8')
        self.assertIn('"type": "connected"', first_event)
        self.assertIn(
            json.dumps(self.user.username, ensure_ascii=False),
            first_event,
        )
