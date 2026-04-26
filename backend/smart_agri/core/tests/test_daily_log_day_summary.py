from datetime import date

from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from django.db import connection

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import DailyLog, Farm



class DailyLogDaySummaryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('daily-log-user', password='pass', is_staff=True)
        supervisor_group, _ = Group.objects.get_or_create(name='Supervisor')
        self.user.groups.add(supervisor_group)

        self.farm = Farm.objects.create(name='مزرعة الاختبار', slug='test-farm', region='الوسطى')
        FarmMembership.objects.create(user=self.user, farm=self.farm, role='Supervisor')

        self.url = reverse('dailylogs-day-summary')
        self.client.force_authenticate(self.user)

    def test_invalid_farm_parameter_returns_bad_request(self):
        response = self.client.get(self.url, {'date': date.today().isoformat(), 'farm': 'not-a-number'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_invalid_date_parameter_returns_bad_request(self):
        response = self.client.get(self.url, {'date': '2024-13-99'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_soft_deleted_farm_returns_log_with_null_name(self):
        log = DailyLog.objects.create(
            farm=self.farm,
            log_date=date.today(),
            notes='اختبار',

            created_by=self.user,
            updated_by=self.user,
        )

        original_farm = {
            'id': self.farm.id,
            'name': self.farm.name,
            'slug': self.farm.slug,
            'region': self.farm.region,
        }

        # Hard-delete the farm record to emulate legacy data that still references it.
        farm_table = Farm._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF')
            cursor.execute(f'DELETE FROM {farm_table} WHERE id = %s', [self.farm.id])
            cursor.execute('PRAGMA foreign_keys = ON')

        try:
            response = self.client.get(self.url, {'date': log.log_date.isoformat()})

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('logs', response.data)
            self.assertEqual(len(response.data['logs']), 1)
            self.assertEqual(response.data['logs'][0]['id'], log.id)
            self.assertEqual(response.data['logs'][0]['farm']['id'], self.farm.id)
            self.assertIsNone(response.data['logs'][0]['farm']['name'])
        finally:
            Farm.objects.create(**original_farm)
            self.farm = Farm.objects.get(pk=original_farm['id'])

