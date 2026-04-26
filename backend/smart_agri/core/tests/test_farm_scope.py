
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Activity, Crop, DailyLog, Farm, Task


class FarmScopeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('member', password='pass123')
        self.client.force_authenticate(self.user)

        self.farm_allowed = Farm.objects.create(name='Farm Alpha', slug='farm-alpha', region='North')
        self.farm_denied = Farm.objects.create(name='Farm Beta', slug='farm-beta', region='South')
        FarmMembership.objects.create(user=self.user, farm=self.farm_allowed, role='Manager')

        self.crop = Crop.objects.create(name='Tomato', mode='Open')
        self.task = Task.objects.create(crop=self.crop, stage='Planting', name='Prepare beds')

        self.allowed_log = DailyLog.objects.create(farm=self.farm_allowed, log_date=date(2024, 1, 1), notes='Allowed note')
        self.denied_log = DailyLog.objects.create(farm=self.farm_denied, log_date=date(2024, 1, 2), notes='Denied note')

        Activity.objects.create(log=self.allowed_log, crop=self.crop, task=self.task, team='Team A')
        Activity.objects.create(log=self.denied_log, crop=self.crop, task=self.task, team='Team B')

    def test_daily_logs_filtered_to_member_farms(self):
        response = self.client.get('/api/v1/daily-logs/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.allowed_log.id)

    def test_activities_filtered_to_member_farms(self):
        response = self.client.get('/api/v1/activities/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['log'], self.allowed_log.id)

    def test_cannot_create_daily_log_for_unowned_farm(self):
        payload = {
            'farm': self.farm_denied.id,
            'log_date': '2024-02-01',
            'notes': 'Should fail',
        }
        response = self.client.post('/api/v1/daily-logs/', payload, format='json')
        self.assertEqual(response.status_code, 403)

    def test_cannot_create_activity_on_foreign_log(self):
        payload = {
            'log': self.denied_log.id,
            'task': self.task.id,
            'team': 'Outsider',
        }
        response = self.client.post('/api/v1/activities/', payload, format='json')
        self.assertEqual(response.status_code, 403)
