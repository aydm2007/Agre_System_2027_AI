from django.test import SimpleTestCase
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from smart_agri.core.services.smart_context_service import SmartContextService

class TestSmartContextService(SimpleTestCase):
    def setUp(self):
        # Mock User and Farm entirely
        self.user = MagicMock()
        self.user.username = 'tester'
        
        self.farm_mock = MagicMock()
        self.farm_mock.id = 1
        
        # Mock farm_set.all() to return our farm mock
        self.user.farm_set.all.return_value = [self.farm_mock]

    @patch('smart_agri.core.services.smart_context_service.Activity') # Patch where it is imported/used
    def test_get_suggestions_returns_last_year_data(self, MockActivity):
        """
        Scenario: Service correctly formatted data from DB.
        """
        today = timezone.now().date()
        date_str = str(today)
        
        # Mock the QuerySet result
        mock_qs = MagicMock()
        mock_qs.values.return_value.annotate.return_value.order_by.return_value = [
            {
                'activity_type': 'Pruning',
                'crop__id': 101,
                'crop__name': 'Mango',
                'location__id': 202,
                'location__name': 'Field A',
                'log__farm__id': 1,
                'count': 5
            }
        ]
        
        # Chain the mock: Activity.objects.filter(...).values(...).annotate(...).order_by(...)
        MockActivity.objects.filter.return_value = mock_qs

        # Call Oracle
        suggestions = SmartContextService.get_suggestions(self.user, date_str)
        
        # Verify Interactions
        self.assertTrue(len(suggestions) > 0)
        suggestion = suggestions[0]
        
        self.assertIn('Pruning', suggestion['label'])
        self.assertEqual(suggestion['data']['location'], 202)
        self.assertEqual(suggestion['data']['crop'], 101)
        self.assertEqual(suggestion['data']['activity_type'], 'Pruning')

    @patch('smart_agri.core.services.smart_context_service.Activity')
    def test_get_suggestions_ignores_irrelevant_data(self, MockActivity):
        """
        Scenario: DB returns nothing.
        """
        today = timezone.now().date()
        date_str = str(today)
        
        # Return empty list
        mock_qs = MagicMock()
        mock_qs.values.return_value.annotate.return_value.order_by.return_value = []
        MockActivity.objects.filter.return_value = mock_qs

        suggestions = SmartContextService.get_suggestions(self.user, date_str)
        self.assertEqual(len(suggestions), 0)
