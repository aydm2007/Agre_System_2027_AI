"""
RLS Middleware Tests - AGRI-MAESTRO Phase 4
Verify user context is set correctly for RLS policies
"""
import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from smart_agri.core.middleware.rls_middleware import RLSMiddleware

User = get_user_model()


class TestRLSMiddleware(TestCase):
    """Test RLS middleware sets PostgreSQL session context"""

    def setUp(self):
        self.factory = RequestFactory()
        
        # Create middleware with dummy get_response
        def dummy_response(request):
            return None
        
        self.middleware = RLSMiddleware(dummy_response)
        
        self.user = User.objects.create_user(
            username='testuser',
            password='test123',
            email='test@example.com'
        )

    def test_authenticated_user_context_set(self):
        """Middleware sets app.user_id for authenticated users"""
        request = self.factory.get('/')
        request.user = self.user

        self.middleware(request)

        # Verify context was set
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.user_id', true)")
            result = cursor.fetchone()
            self.assertEqual(result[0], str(self.user.id))

    def test_anonymous_user_no_context(self):
        """Middleware clears context for anonymous users"""
        request = self.factory.get('/')
        request.user = AnonymousUser()

        self.middleware(request)

        # Context should be NULL or empty
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.user_id', true)")
            result = cursor.fetchone()
            self.assertIn(result[0], [None, '', 'NULL'])

    def test_middleware_called_for_each_request(self):
        """Middleware executes for every request"""
        request1 = self.factory.get('/')
        request1.user = self.user

        response1 = self.middleware(request1)
        
        # Verify middleware was called (response is None from dummy)
        self.assertIsNone(response1)

    def test_context_survives_transaction(self):
        """PostgreSQL context persists within transaction"""
        request = self.factory.get('/')
        request.user = self.user

        self.middleware(request)

        # Multiple queries in same transaction see same context
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.user_id', true)")
            result1 = cursor.fetchone()[0]

            cursor.execute("SELECT current_setting('app.user_id', true)")
            result2 = cursor.fetchone()[0]

            self.assertEqual(result1, result2)
            self.assertEqual(result1, str(self.user.id))


# Run with: python manage.py test core.tests.test_rls_middleware
