from datetime import date

from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Activity, DailyLog, Farm


class ActivityTeamSuggestionsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('team-user', password='pass', is_staff=True)
        supervisor_group, _ = Group.objects.get_or_create(name='Supervisor')
        self.user.groups.add(supervisor_group)

        self.primary_farm = Farm.objects.create(name='المزرعة الأساسية', slug='farm-main', region='وسط')
        self.other_farm = Farm.objects.create(name='مزرعة أخرى', slug='farm-other', region='شمال')

        FarmMembership.objects.create(user=self.user, farm=self.primary_farm, role='Supervisor')

        self.primary_log = DailyLog.objects.create(farm=self.primary_farm, log_date=date.today())
        self.other_log = DailyLog.objects.create(farm=self.other_farm, log_date=date.today())

        # Activity for another farm that should never appear in the results
        Activity.objects.create(log=self.other_log, team='فريق خارجي')

        self.client.force_authenticate(self.user)
        self.url = reverse('activities-team-suggestions')

    def test_requires_farm_id(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_enforces_farm_permissions(self):
        response = self.client.get(self.url, {'farm_id': self.other_farm.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_unique_names(self):
        Activity.objects.create(log=self.primary_log, team='علي محمد، فهد السلمان\nمحمود')
        Activity.objects.create(log=self.primary_log, team='علي محمد\nسارة التميمي')

        response = self.client.get(self.url, {'farm_id': self.primary_farm.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, ['علي محمد', 'فهد السلمان', 'محمود', 'سارة التميمي'])

    def test_filters_by_query(self):
        Activity.objects.create(log=self.primary_log, team='سارة التميمي\nأحمد سالم')
        Activity.objects.create(log=self.primary_log, team='علي محمد')

        response = self.client.get(self.url, {'farm_id': self.primary_farm.id, 'q': 'س'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, ['سارة التميمي'])
