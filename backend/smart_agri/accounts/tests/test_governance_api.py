from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmGovernanceProfile, FarmMembership, RoleDelegation
from smart_agri.core.models import Farm


class GovernanceApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            'governance_admin',
            password='pass123',
            email='governance@example.com',
            is_staff=True,
            is_superuser=True,
        )
        self.principal = User.objects.create_user('principal', password='pass123')
        self.delegate = User.objects.create_user('delegate', password='pass123')
        self.farm = Farm.objects.create(name='Governance Farm', slug='governance-farm', region='North')
        FarmMembership.objects.create(user=self.principal, farm=self.farm, role='مدير المزرعة')
        self.profile = FarmGovernanceProfile.objects.create(
            farm=self.farm,
            tier=FarmGovernanceProfile.TIER_MEDIUM,
            rationale='baseline profile',
            approved_by=self.user,
            approved_at=timezone.now(),
        )
        self.delegation = RoleDelegation.objects.create(
            farm=self.farm,
            principal_user=self.principal,
            delegate_user=self.delegate,
            role='مدير المزرعة',
            reason='temporary coverage',
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=3),
            is_active=True,
            approved_by=self.user,
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)

    def test_farm_governance_profiles_list_exposes_capabilities_meta(self):
        response = self.client.get('/api/v1/governance/farm-profiles/', {'farm': self.farm.id})
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertIn('meta', response.data)
        self.assertTrue(response.data['meta']['can_manage'])
        profile_payload = response.data['results'][0]
        self.assertIn('capabilities', profile_payload)
        self.assertTrue(profile_payload['capabilities']['can_update'])

    def test_role_delegations_list_exposes_capabilities_meta(self):
        response = self.client.get('/api/v1/governance/role-delegations/', {'farm': self.farm.id})
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertIn('meta', response.data)
        self.assertTrue(response.data['meta']['can_manage'])
        delegation_payload = response.data['results'][0]
        self.assertIn('capabilities', delegation_payload)
        self.assertTrue(delegation_payload['capabilities']['can_update'])
        self.assertTrue(delegation_payload['capabilities']['can_delete'])
