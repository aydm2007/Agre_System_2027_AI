from unittest.mock import patch

from django.db import ProgrammingError
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from datetime import timedelta

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Farm, PolicyPackage
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.policy_engine_service import PolicyEngineService


class ModePolicyAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'policy_manager',
            password='pass',
            is_staff=True,
            is_superuser=True,
        )
        self.farm = Farm.objects.create(name='Policy Farm', slug='policy-farm', region='A')
        FarmMembership.objects.create(user=self.user, farm=self.farm, role='Manager')
        self.settings = FarmSettings.objects.create(farm=self.farm)

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _idem(self, suffix):
        return {"HTTP_X_IDEMPOTENCY_KEY": f"policy-api-{suffix}"}

    def test_farm_settings_list_exposes_policy_fields(self):
        response = self.client.get(reverse('farm-settings-list'), {'farm': self.farm.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['results'][0]
        self.assertEqual(payload['mode'], FarmSettings.MODE_SIMPLE)
        self.assertEqual(payload['cost_visibility'], FarmSettings.COST_VISIBILITY_SUMMARIZED)
        self.assertEqual(payload['treasury_visibility'], FarmSettings.TREASURY_VISIBILITY_HIDDEN)
        self.assertFalse(payload['allow_creator_self_variance_approval'])
        self.assertTrue(payload['show_daily_log_smart_card'])
        self.assertFalse(payload['remote_site'])
        self.assertFalse(payload['weekly_remote_review_required'])
        self.assertTrue(payload['mandatory_attachment_for_cash'])
        self.assertEqual(payload['attachment_scan_mode'], FarmSettings.ATTACHMENT_SCAN_MODE_HEURISTIC)
        self.assertIn('remote_site', payload['policy_snapshot'])
        self.assertIn('attachment_scan_mode', payload['policy_snapshot'])
        self.assertIn('policy_source', payload)
        self.assertIn('effective_policy_payload', payload)
        self.assertIn('policy_field_catalog', payload)
        self.assertEqual(payload['policy_snapshot']['visibility_level'], 'operations_only')
        self.assertFalse(payload['policy_snapshot']['allow_creator_self_variance_approval'])
        self.assertTrue(payload['policy_snapshot']['show_daily_log_smart_card'])

    def test_farm_settings_patch_updates_policy_contract(self):
        response = self.client.patch(
            reverse('farm-settings-detail', args=[self.settings.id]),
            {
                'mode': FarmSettings.MODE_STRICT,
                'cost_visibility': FarmSettings.COST_VISIBILITY_FULL,
                'variance_behavior': FarmSettings.VARIANCE_BEHAVIOR_BLOCK,
                'approval_profile': FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE,
                'contract_mode': FarmSettings.CONTRACT_MODE_FULL_ERP,
                'treasury_visibility': FarmSettings.TREASURY_VISIBILITY_VISIBLE,
                'fixed_asset_mode': FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION,
                'allow_creator_self_variance_approval': True,
                'show_daily_log_smart_card': False,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.mode, FarmSettings.MODE_STRICT)
        self.assertEqual(self.settings.cost_visibility, FarmSettings.COST_VISIBILITY_FULL)
        self.assertEqual(self.settings.variance_behavior, FarmSettings.VARIANCE_BEHAVIOR_BLOCK)
        self.assertTrue(self.settings.allow_creator_self_variance_approval)
        self.assertFalse(self.settings.show_daily_log_smart_card)
        self.assertEqual(response.data['policy_snapshot']['contract_mode'], FarmSettings.CONTRACT_MODE_FULL_ERP)
        self.assertEqual(response.data['visibility_level'], 'full_erp')

    def test_system_mode_includes_policy_snapshot(self):
        self.settings.mode = FarmSettings.MODE_STRICT
        self.settings.cost_visibility = FarmSettings.COST_VISIBILITY_FULL
        self.settings.save(update_fields=['mode', 'cost_visibility'])

        response = self.client.get(reverse('system-mode-list'), {'farm': self.farm.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mode'], FarmSettings.MODE_STRICT)
        self.assertTrue(response.data['strict_erp_mode'])
        self.assertEqual(response.data['visibility_level'], 'full_erp')
        self.assertEqual(response.data['cost_display_mode'], FarmSettings.COST_VISIBILITY_FULL)
        self.assertEqual(response.data['policy_snapshot']['mode'], FarmSettings.MODE_STRICT)
        self.assertFalse(response.data['legacy_mode_divergence']['detected'])

    def test_farm_settings_fallback_includes_policy_snapshot(self):
        with patch(
            'smart_agri.core.api.viewsets.settings.FarmSettings.objects.get_or_create',
            side_effect=ProgrammingError('table missing'),
        ):
            response = self.client.get(reverse('farm-settings-list'), {'farm': self.farm.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['results'][0]
        self.assertEqual(payload['mode'], FarmSettings.MODE_SIMPLE)
        self.assertEqual(payload['visibility_level'], 'operations_only')
        self.assertEqual(payload['cost_visibility'], FarmSettings.COST_VISIBILITY_SUMMARIZED)
        self.assertEqual(payload['policy_snapshot']['mode'], FarmSettings.MODE_SIMPLE)
        self.assertFalse(payload['allow_creator_self_variance_approval'])
        self.assertTrue(payload['show_daily_log_smart_card'])
        self.assertIn('policy_field_catalog', payload)

    def test_system_mode_reports_legacy_mode_divergence(self):
        from smart_agri.core.models.settings import SystemSettings

        global_settings = SystemSettings.get_settings()
        global_settings.strict_erp_mode = True
        global_settings.save(update_fields=['strict_erp_mode', 'updated_at'])
        response = self.client.get(reverse('system-mode-list'), {'farm': self.farm.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['strict_erp_mode'])
        self.assertTrue(response.data['legacy_mode_divergence']['detected'])
        self.assertTrue(response.data['legacy_global_strict_erp_mode'])

    def test_system_mode_defaults_to_superuser_membership_scope(self):
        strict_farm = Farm.objects.create(name='Strict Farm', slug='strict-farm', region='B')
        FarmSettings.objects.create(farm=strict_farm, mode=FarmSettings.MODE_STRICT)

        response = self.client.get(reverse('system-mode-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['farm_id'], self.farm.id)
        self.assertEqual(response.data['mode'], FarmSettings.MODE_SIMPLE)
        self.assertFalse(response.data['strict_erp_mode'])

    def test_farm_settings_legacy_invalid_policy_remains_readable(self):
        self.settings.contract_mode = FarmSettings.CONTRACT_MODE_FULL_ERP
        self.settings.save(update_fields=['contract_mode'])

        response = self.client.get(reverse('farm-settings-list'), {'farm': self.farm.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['results'][0]
        self.assertEqual(payload['contract_mode'], FarmSettings.CONTRACT_MODE_FULL_ERP)
        self.assertEqual(payload['policy_source'], 'farm_settings_legacy_invalid')
        self.assertEqual(
            payload['effective_policy_payload']['dual_mode_policy']['contract_mode'],
            FarmSettings.CONTRACT_MODE_FULL_ERP,
        )

    def test_farm_settings_effective_policy_action_returns_flat_policy(self):
        response = self.client.get(reverse('farm-settings-effective-policy', args=[self.settings.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['farm_id'], self.farm.id)
        self.assertIn('flat_policy', response.data)
        self.assertIn('field_catalog', response.data)

    def test_farm_settings_policy_diff_previews_patch(self):
        response = self.client.post(
            reverse('farm-settings-policy-diff', args=[self.settings.id]),
            {'mode': FarmSettings.MODE_STRICT},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['eligible'])
        self.assertIn('mode', response.data['changed_fields'])

    def test_policy_version_simulate_returns_activation_eligibility(self):
        package = PolicyPackage.objects.create(
            name='API Package',
            slug='api-package',
            created_by=self.user,
            updated_by=self.user,
        )
        payload = PolicyEngineService.default_policy_payload()
        payload['dual_mode_policy']['mode'] = FarmSettings.MODE_STRICT
        version = PolicyEngineService.create_version(
            actor=self.user,
            package=package,
            version_label='v1',
            payload=payload,
        )
        PolicyEngineService.approve_version(actor=self.user, instance=version)

        response = self.client.get(
            reverse('policy-versions-simulate', args=[version.id]),
            {'farm': self.farm.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['eligible'])
        self.assertIn('diff', response.data)
        self.assertIn('simulation', response.data)

    def test_policy_list_payloads_expose_capabilities(self):
        package = PolicyPackage.objects.create(
            name='Caps Package',
            slug='caps-package',
            created_by=self.user,
            updated_by=self.user,
        )
        payload = PolicyEngineService.default_policy_payload()
        version = PolicyEngineService.create_version(
            actor=self.user,
            package=package,
            version_label='caps-v1',
            payload=payload,
        )
        PolicyEngineService.approve_version(actor=self.user, instance=version)
        activation = PolicyEngineService.create_activation_request(
            actor=self.user,
            farm=self.farm,
            policy_version=version,
            rationale='caps test',
        )
        exception = PolicyEngineService.create_exception_request(
            actor=self.user,
            farm=self.farm,
            requested_patch={'mandatory_attachment_for_cash': False},
            rationale='caps test',
            effective_from=timezone.now(),
            effective_to=timezone.now() + timedelta(days=1),
        )

        packages_response = self.client.get(reverse('policy-packages-list'))
        versions_response = self.client.get(reverse('policy-versions-list'))
        activations_response = self.client.get(reverse('policy-activation-requests-list'), {'farm': self.farm.id})
        exceptions_response = self.client.get(reverse('policy-exception-requests-list'), {'farm': self.farm.id})

        self.assertEqual(packages_response.status_code, status.HTTP_200_OK)
        self.assertEqual(versions_response.status_code, status.HTTP_200_OK)
        self.assertEqual(activations_response.status_code, status.HTTP_200_OK)
        self.assertEqual(exceptions_response.status_code, status.HTTP_200_OK)

        package_payload = packages_response.data['results'][0]
        version_payload = next(item for item in versions_response.data['results'] if item['id'] == version.id)
        activation_payload = next(item for item in activations_response.data['results'] if item['id'] == activation.id)
        exception_payload = next(item for item in exceptions_response.data['results'] if item['id'] == exception.id)

        self.assertIn('capabilities', package_payload)
        self.assertTrue(package_payload['capabilities']['can_manage'])
        self.assertIn('capabilities', version_payload)
        self.assertTrue(version_payload['capabilities']['can_retire'])
        self.assertTrue(version_payload['capabilities']['can_simulate'])
        self.assertIn('capabilities', activation_payload)
        self.assertTrue(activation_payload['capabilities']['can_submit'])
        self.assertIn('capabilities', exception_payload)
        self.assertTrue(exception_payload['capabilities']['can_submit'])

    def test_policy_version_diff_against_effective_farm_policy(self):
        package = PolicyPackage.objects.create(
            name='Diff API Package',
            slug='diff-api-package',
            created_by=self.user,
            updated_by=self.user,
        )
        payload = PolicyEngineService.default_policy_payload()
        payload['dual_mode_policy']['mode'] = FarmSettings.MODE_STRICT
        version = PolicyEngineService.create_version(
            actor=self.user,
            package=package,
            version_label='v1',
            payload=payload,
        )

        response = self.client.post(
            reverse('policy-versions-diff', args=[version.id]),
            {'farm': self.farm.id},
            format='json',
            **self._idem('version-diff'),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comparison_mode'], 'version_to_farm')
        self.assertIn('mode', response.data['changed_fields'])

    def test_policy_exception_request_lifecycle_updates_effective_policy(self):
        response = self.client.post(
            reverse('policy-exception-requests-list'),
            {
                'farm': self.farm.id,
                'requested_patch': {
                    'mandatory_attachment_for_cash': False,
                    'attachment_scan_mode': FarmSettings.ATTACHMENT_SCAN_MODE_HEURISTIC,
                },
                'rationale': 'Temporary attachment policy exception.',
                'effective_from': timezone.now().isoformat(),
                'effective_to': (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format='json',
            **self._idem('exception-create'),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        request_id = response.data['id']

        response = self.client.post(
            reverse('policy-exception-requests-submit', args=[request_id]),
            {},
            format='json',
            **self._idem('exception-submit'),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'pending')

        response = self.client.post(
            reverse('policy-exception-requests-approve', args=[request_id]),
            {},
            format='json',
            **self._idem('exception-approve'),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'approved')

        response = self.client.post(
            reverse('policy-exception-requests-apply', args=[request_id]),
            {},
            format='json',
            **self._idem('exception-apply'),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'applied')

        settings_response = self.client.get(reverse('farm-settings-list'), {'farm': self.farm.id})
        self.assertEqual(settings_response.status_code, status.HTTP_200_OK)
        payload = settings_response.data['results'][0]
        self.assertIsNotNone(payload['active_policy_exception'])
        self.assertEqual(payload['active_policy_exception']['status'], 'applied')
        effective_fields = payload['effective_policy_fields']
        mandatory_field = next(
            item for item in effective_fields if item['field'] == 'mandatory_attachment_for_cash'
        )
        self.assertEqual(mandatory_field['source'], 'policy_exception')
        self.assertFalse(mandatory_field['value'])

    def test_policy_package_usage_snapshot_endpoint_returns_summary(self):
        response = self.client.get(reverse('policy-packages-usage-snapshot'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', response.data)
        self.assertIn('packages', response.data)

    def test_policy_activation_timeline_snapshot_endpoint_returns_counts(self):
        response = self.client.get(reverse('policy-activation-requests-timeline-snapshot'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('counts_by_status', response.data)
        self.assertIn('latest_events', response.data)

    def test_policy_exception_pressure_snapshot_endpoint_returns_grouping(self):
        response = self.client.get(reverse('policy-exception-requests-pressure-snapshot'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('open_by_farm', response.data)
        self.assertIn('open_by_field_family', response.data)
