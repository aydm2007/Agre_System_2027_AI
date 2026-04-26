"""API Tests for CostConfiguration endpoint."""
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status as http_status

from smart_agri.core.models import Farm, CostConfiguration
from django.contrib.auth import get_user_model


class CostConfigurationAPITests(TestCase):
    """Test suite for CostConfiguration API endpoint."""
    
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.farm = Farm.objects.create(
            name='Test Farm API',
            slug='test-farm-api',
            region='North'
        )
    
    def test_create_cost_configuration(self):
        """Test creating a new CostConfiguration via API."""
        url = '/api/v1/cost-configurations/'
        data = {
            'farm': self.farm.id,
            'overhead_rate_per_hectare': '75.00',
            'currency': 'YER'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data['overhead_rate_per_hectare']), Decimal('75.00'))
    
    def test_get_cost_configuration(self):
        """Test retrieving CostConfiguration via API."""
        config = CostConfiguration.objects.create(
            farm=self.farm,
            overhead_rate_per_hectare=Decimal('100.00'),
            currency='SAR'
        )
        
        url = f'/api/v1/cost-configurations/{config.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['farm'], self.farm.id)
        self.assertEqual(Decimal(response.data['overhead_rate_per_hectare']), Decimal('100.00'))
    
    def test_update_cost_configuration(self):
        """Test updating CostConfiguration via API."""
        config = CostConfiguration.objects.create(
            farm=self.farm,
            overhead_rate_per_hectare=Decimal('50.00'),
            currency='YER'
        )
        
        url = f'/api/v1/cost-configurations/{config.id}/'
        data = {'overhead_rate_per_hectare': '150.00'}
        
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        
        config.refresh_from_db()
        self.assertEqual(config.overhead_rate_per_hectare, Decimal('150.00'))
    
    def test_list_cost_configurations(self):
        """Test listing all CostConfigurations via API."""
        farm2 = Farm.objects.create(name='Farm 2', slug='farm-2', region='South')
        CostConfiguration.objects.create(farm=self.farm, overhead_rate_per_hectare=Decimal('60.00'))
        CostConfiguration.objects.create(farm=farm2, overhead_rate_per_hectare=Decimal('80.00'))
        
        url = '/api/v1/cost-configurations/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)
    
    def test_delete_cost_configuration(self):
        """Test soft-deleting CostConfiguration via API."""
        config = CostConfiguration.objects.create(
            farm=self.farm,
            overhead_rate_per_hectare=Decimal('50.00')
        )
        
        url = f'/api/v1/cost-configurations/{config.id}/'
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, http_status.HTTP_204_NO_CONTENT)
