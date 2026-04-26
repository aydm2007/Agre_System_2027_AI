from django.test import SimpleTestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.management.commands.bootstrap_postgres_foundation import TIER_POLICY_DEFAULTS
from smart_agri.core.management.commands.seed_full_system import USER_DEFINITIONS
from smart_agri.core.management.commands.seed_roles import ROLE_PERMISSIONS
from smart_agri.core.models import Farm, FarmSettings


class SeedReferenceBootstrapTests(SimpleTestCase):
    def test_seed_full_system_roles_are_canonical_arabic_values(self):
        valid_roles = {code for code, _ in FarmMembership.ROLE_CHOICES}
        valid_groups = set(ROLE_PERMISSIONS.keys())
        for user_def in USER_DEFINITIONS:
            self.assertIn(user_def['membership_role'], valid_roles)
            self.assertIn(user_def['group'], valid_groups)

    def test_tier_policy_defaults_match_reference_boundaries(self):
        self.assertEqual(TIER_POLICY_DEFAULTS[Farm.TIER_SMALL]['mode'], FarmSettings.MODE_SIMPLE)
        self.assertEqual(TIER_POLICY_DEFAULTS[Farm.TIER_MEDIUM]['mode'], FarmSettings.MODE_STRICT)
        self.assertEqual(TIER_POLICY_DEFAULTS[Farm.TIER_LARGE]['mode'], FarmSettings.MODE_STRICT)
        self.assertTrue(TIER_POLICY_DEFAULTS[Farm.TIER_MEDIUM]['weekly_remote_review_required'])
        self.assertTrue(TIER_POLICY_DEFAULTS[Farm.TIER_LARGE]['weekly_remote_review_required'])
        self.assertFalse(TIER_POLICY_DEFAULTS[Farm.TIER_MEDIUM]['single_finance_officer_allowed'])
        self.assertFalse(TIER_POLICY_DEFAULTS[Farm.TIER_LARGE]['single_finance_officer_allowed'])
