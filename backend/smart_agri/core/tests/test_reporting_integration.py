
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from django.urls import reverse
from smart_agri.core.models import Farm, DailyLog, Activity, Task, Crop, Location
from decimal import Decimal
from django.utils import timezone

@pytest.mark.django_db
class TestReportingIntegration:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='test_user', password='password')
        self.client.force_authenticate(user=self.user)
        
        # Setup basic data
        self.farm = Farm.objects.create(name="Test Farm", region="Test Region")
        # Assuming membership logic or user handling in tests. 
        # For simplicity, if perms logic requires it, we'd add it here.
        # But we previously saw simple logic.
        
        # Create Log
        self.log = DailyLog.objects.create(
            farm=self.farm, 
            log_date=timezone.now().date(),
            created_by=self.user
        )
        
        # Create Activity
        self.crop = Crop.objects.create(name="Wheat")
        self.task = Task.objects.create(name="Tilling", crop=self.crop)
        self.location = Location.objects.create(name="Field A", farm=self.farm)
        
        self.activity = Activity.objects.create(
            log=self.log,
            crop=self.crop,
            task=self.task,
            location=self.location,
            cost_total=Decimal("100.50"),
            days_spent=Decimal("5.0")
        )

    def test_advanced_report_success(self):
        """Direct GET should remain usable without explicit section scope."""
        url = reverse('advanced_report')
        self.user.is_superuser = True
        self.user.save()
        
        response = self.client.get(url, {'start': '2020-01-01'})
        assert response.status_code == 200
        data = response.json()

        assert 'summary' in data
        assert 'metrics' in data['summary']
        assert data['summary']['metrics']['total_hours'] == 5.0
        assert data['section_scope'] == ['summary']
        assert data['details_meta']['returned'] >= 1
        assert len(data['details']) >= 1

    def test_advanced_report_summary_only_scope_skips_details(self):
        url = reverse('advanced_report')
        self.user.is_superuser = True
        self.user.save()

        response = self.client.get(
            url,
            {
                'start': '2020-01-01',
                'section_scope': ['summary'],
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data['section_scope'] == ['summary']
        assert data['details'] == []
        assert data['details_meta']['returned'] == 0

    def test_advanced_report_explicit_detail_scope_returns_paginated_details(self):
        url = reverse('advanced_report')
        self.user.is_superuser = True
        self.user.save()

        response = self.client.get(
            url,
            {
                'start': '2020-01-01',
                'section_scope': ['summary', 'activities', 'detailed_tables'],
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data['details_meta']['returned'] >= 1
        assert len(data['details']) >= 1
        
    def test_advanced_report_500_handling(self):
        """Test that known runtime failures return strict 500 response."""
        self.user.is_superuser = True
        self.user.save()
        
        from unittest.mock import patch
        
        with patch('smart_agri.core.models.Activity.objects.filter', side_effect=ValueError("Database Boom")):
             url = reverse('advanced_report')
             response = self.client.get(url)
             
             assert response.status_code == 500
             data = response.json()
             assert 'detail' in data
             assert "Database Boom" in data['detail']

    def test_dashboard_stats_success(self):
        url = reverse('dashboard_stats')
        self.user.is_superuser = True
        self.user.save()
        
        response = self.client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert 'financials' in data
        assert 'distributable_surplus' in data['financials']
        assert 'net_profit' in data['financials']
        assert data['financials']['distributable_surplus'] == data['financials']['net_profit']

    def test_dashboard_stats_internal_failure_returns_500(self):
        from unittest.mock import patch

        url = reverse('dashboard_stats')
        with patch('smart_agri.core.api.reporting.user_farm_ids', side_effect=ValueError("Broken farm scope")):
            response = self.client.get(url)
            assert response.status_code == 500
