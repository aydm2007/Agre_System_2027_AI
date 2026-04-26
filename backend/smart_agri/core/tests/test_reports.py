from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import (
    Activity,
    Crop,
    CropVariety,
    DailyLog,
    Farm,
    Location,
    LocationTreeStock,
    Task,
)


class ReportsPerennialSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('reports-user', password='secret')
        self.client.force_authenticate(self.user)

        self.farm = Farm.objects.create(name='Farm Oasis', slug='farm-oasis', region='South')
        FarmMembership.objects.create(user=self.user, farm=self.farm, role='Manager')

        self.location = Location.objects.create(farm=self.farm, name='Block A')
        self.crop = Crop.objects.create(name='نخيل', is_perennial=True)
        self.variety = CropVariety.objects.create(crop=self.crop, name='سكري')
        self.task = Task.objects.create(
            crop=self.crop,
            name='خدمة الري',
            stage='عناية',
            requires_tree_count=True,
            is_perennial_procedure=True,
        )

        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date=date(2024, 8, 1),
            created_by=self.user,
            updated_by=self.user,
        )

        Activity.objects.create(
            log=self.log,
            crop=self.crop,
            task=self.task,
            location=self.location,
            variety=self.variety,
            activity_tree_count=45,
            tree_count_delta=5,
        )

        LocationTreeStock.objects.create(
            location=self.location,
            crop_variety=self.variety,
            current_tree_count=120,
        )

    def test_daily_summary_includes_perennial_metrics(self):
        response = self.client.get(
            '/api/v1/reports/',
            {
                'start': '2024-08-01',
                'end': '2024-08-01',
                'farm': str(self.farm.id),
            },
        )

        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn('perennial', payload)

        perennial = payload['perennial']
        self.assertEqual(perennial['activities'], 1)
        self.assertEqual(perennial['trees_serviced'], 45)
        self.assertEqual(perennial['net_tree_delta'], 5)
        self.assertEqual(perennial['current_tree_count'], 120)

        entries = perennial.get('entries') or []
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry['activities'], 1)
        self.assertEqual(entry['trees_serviced'], 45)
        self.assertEqual(entry['net_tree_delta'], 5)
        self.assertEqual(entry['current_tree_count'], 120)
        self.assertEqual(entry['crop']['id'], self.crop.id)
        self.assertEqual(entry['variety']['id'], self.variety.id)
        self.assertEqual(entry['location']['id'], self.location.id)

    def test_reports_ignore_invalid_numeric_filters(self):
        response = self.client.get(
            '/api/v1/reports/',
            {
                'start': '2024-08-01',
                'end': '2024-08-01',
                'farm': str(self.farm.id),
                'crop': 'undefined',
                'task': 'not-a-number',
                'location': 'null',
                'supervisor': 'abc',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['metrics']['activities'], 1)
