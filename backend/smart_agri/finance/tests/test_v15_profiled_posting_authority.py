from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService


class ProfiledPostingAuthorityTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="Test Farm")
        self.settings = FarmSettings.objects.create(
            farm=self.farm,
            mode=FarmSettings.MODE_STRICT,
            approval_profile=FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE,
        )
        self.user = User.objects.create_user(username="u1", password="pass")

    def test_strict_finance_requires_sector_final_authority(self):
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="المدير المالي للمزرعة")
        with self.assertRaises(ValidationError):
            FarmFinanceAuthorityService.require_profiled_posting_authority(
                user=self.user, farm=self.farm, action_label="posting"
            )

    def test_sector_final_role_passes(self):
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="المدير المالي لقطاع المزارع")
        FarmFinanceAuthorityService.require_profiled_posting_authority(
            user=self.user, farm=self.farm, action_label="posting"
        )

    def test_tiered_profile_allows_farm_finance_manager(self):
        self.settings.approval_profile = FarmSettings.APPROVAL_PROFILE_TIERED
        self.settings.save(update_fields=["approval_profile"])
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="المدير المالي للمزرعة")
        FarmFinanceAuthorityService.require_profiled_posting_authority(
            user=self.user, farm=self.farm, action_label="posting"
        )

    def test_medium_farm_rejects_local_accountant_without_farm_finance_manager(self):
        self.farm.tier = "MEDIUM"
        self.farm.save(update_fields=["tier"])
        self.settings.approval_profile = FarmSettings.APPROVAL_PROFILE_TIERED
        self.settings.save(update_fields=["approval_profile"])
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="محاسب المزرعة")
        with self.assertRaises(ValidationError):
            FarmFinanceAuthorityService.require_profiled_posting_authority(
                user=self.user, farm=self.farm, action_label="posting"
            )

    def test_small_farm_allows_acting_role_when_single_officer_enabled(self):
        self.farm.tier = "SMALL"
        self.farm.save(update_fields=["tier"])
        self.settings.approval_profile = FarmSettings.APPROVAL_PROFILE_TIERED
        self.settings.single_finance_officer_allowed = True
        self.settings.save(update_fields=["approval_profile", "single_finance_officer_allowed"])
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="رئيس الحسابات")
        FarmFinanceAuthorityService.require_profiled_posting_authority(
            user=self.user, farm=self.farm, action_label="posting"
        )

    def test_simple_mode_rejects_even_sector_final_authority(self):
        self.settings.mode = FarmSettings.MODE_SIMPLE
        self.settings.save(update_fields=["mode"])
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="المدير المالي لقطاع المزارع")
        with self.assertRaises(ValidationError):
            FarmFinanceAuthorityService.require_strict_cycle_authority(
                user=self.user,
                farm=self.farm,
                action_label="posting",
            )
            
    # --- M2.7 Expanded Tests for the 6 core financial operations ---

    def _assert_strict_posting_requires_sector_authority(self, action_label):
        # Under STRICT_FINANCE profile, a Farm Finance Manager cannot post.
        self.settings.approval_profile = FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE
        self.settings.save()
        user_ffm = User.objects.create_user(username=f"ffm_{action_label}", password="pw")
        FarmMembership.objects.create(user=user_ffm, farm=self.farm, role="المدير المالي للمزرعة")
        
        with self.assertRaises(ValidationError):
            FarmFinanceAuthorityService.require_profiled_posting_authority(
                user=user_ffm, farm=self.farm, action_label=action_label
            )
            
        # But a Sector Finance Director can.
        user_sfd = User.objects.create_user(username=f"sfd_{action_label}", password="pw")
        FarmMembership.objects.create(user=user_sfd, farm=self.farm, role="المدير المالي لقطاع المزارع")
        FarmFinanceAuthorityService.require_profiled_posting_authority(
            user=user_sfd, farm=self.farm, action_label=action_label
        )

    def test_profiled_posting_supplier_settlement(self):
        self._assert_strict_posting_requires_sector_authority("supplier_settlement")

    def test_profiled_posting_petty_cash(self):
        self._assert_strict_posting_requires_sector_authority("petty_cash_settlement")

    def test_profiled_posting_contract_payment(self):
        self._assert_strict_posting_requires_sector_authority("contract_payment")

    def test_profiled_posting_fixed_assets(self):
        self._assert_strict_posting_requires_sector_authority("fixed_asset_capitalization")

    def test_profiled_posting_fuel_reconciliation(self):
        self._assert_strict_posting_requires_sector_authority("fuel_reconciliation")

    def test_profiled_posting_fiscal_close(self):
        self._assert_strict_posting_requires_sector_authority("fiscal_close")
