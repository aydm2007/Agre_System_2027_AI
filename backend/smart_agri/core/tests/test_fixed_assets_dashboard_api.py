from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Asset, AuditLog, Farm, IdempotencyRecord
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import FinancialLedger, FiscalPeriod, FiscalYear


class FixedAssetsDashboardAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("asset_manager", password="pass", is_staff=True, is_superuser=True)
        self.farm = Farm.objects.create(name="Asset Farm", slug="asset-farm", region="A")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")
        self.settings = FarmSettings.objects.create(
            farm=self.farm,
            mode=FarmSettings.MODE_SIMPLE,
            cost_visibility=FarmSettings.COST_VISIBILITY_SUMMARIZED,
            fixed_asset_mode=FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY,
        )
        Asset.objects.create(
            farm=self.farm,
            category="Solar",
            asset_type="solar_array",
            code="SOL-1",
            name="Solar Array 1",
            purchase_value="120000.00",
            salvage_value="10000.00",
            accumulated_depreciation="45000.00",
            useful_life_years=10,
        )
        Asset.objects.create(
            farm=self.farm,
            category="Machinery",
            asset_type="tractor",
            code="TR-1",
            name="Field Tractor",
            purchase_value="80000.00",
            salvage_value="5000.00",
            accumulated_depreciation="10000.00",
            useful_life_years=8,
            operational_cost_per_hour="250.00",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.solar_asset = Asset.objects.get(code="SOL-1")
        self.tractor_asset = Asset.objects.get(code="TR-1")

    def _ensure_open_period(self):
        fiscal_year = FiscalYear.objects.create(
            farm=self.farm,
            year=2026,
            start_date="2026-01-01",
            end_date="2026-12-31",
        )
        FiscalPeriod.objects.create(
            fiscal_year=fiscal_year,
            month=1,
            start_date="2026-01-01",
            end_date="2026-01-31",
            status=FiscalPeriod.STATUS_OPEN,
            is_closed=False,
        )

    def test_fixed_assets_dashboard_returns_policy_snapshot(self):
        response = self.client.get(reverse("fixed-assets-list"), {"farm_id": self.farm.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["policy_snapshot"]["fixed_asset_mode"], FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY)
        self.assertEqual(response.data["cost_display_mode"], FarmSettings.COST_VISIBILITY_SUMMARIZED)
        self.assertEqual(response.data["summary"]["assets_count"], 2)
        self.assertEqual(response.data["results"][0]["visibility_level"], "operations_only")
        self.assertFalse(response.data["summary"]["report_flags"]["line_amounts_visible"])
        self.assertEqual(response.data["summary"]["total_purchase_value"], "200000.00")
        self.assertIsNone(response.data["summary"]["total_accumulated_depreciation"])
        self.assertTrue(response.data["results"][0]["amounts_redacted"])
        self.assertIsNone(response.data["results"][0]["purchase_value"])
        self.assertIsNone(response.data["results"][0]["book_value"])

    def test_fixed_assets_dashboard_reflects_full_capitalization_policy(self):
        self.settings.mode = FarmSettings.MODE_STRICT
        self.settings.cost_visibility = FarmSettings.COST_VISIBILITY_FULL
        self.settings.fixed_asset_mode = FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION
        self.settings.save(update_fields=["mode", "cost_visibility", "fixed_asset_mode"])

        response = self.client.get(reverse("fixed-assets-list"), {"farm_id": self.farm.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["policy_snapshot"]["fixed_asset_mode"], FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION)
        self.assertEqual(response.data["visibility_level"], "full_erp")
        self.assertEqual(response.data["cost_display_mode"], FarmSettings.COST_VISIBILITY_FULL)
        self.assertTrue(response.data["summary"]["report_flags"]["requires_capitalization_controls"])
        self.assertTrue(response.data["summary"]["report_flags"]["line_amounts_visible"])
        self.assertEqual(response.data["summary"]["total_purchase_value"], "200000.00")
        self.assertEqual(response.data["summary"]["total_accumulated_depreciation"], "55000.00")
        self.assertFalse(response.data["results"][0]["amounts_redacted"])
        self.assertEqual(response.data["results"][0]["purchase_value"], "80000.00")
        self.assertEqual(response.data["results"][0]["book_value"], "70000.00")

    def test_fixed_assets_dashboard_filters_by_category(self):
        response = self.client.get(
            reverse("fixed-assets-list"),
            {"farm_id": self.farm.id, "category": "Solar"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["category"], "Solar")

    def test_capitalize_action_posts_ledger_audit_and_idempotency(self):
        self._ensure_open_period()
        self.settings.mode = FarmSettings.MODE_STRICT
        self.settings.fixed_asset_mode = FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION
        self.settings.cost_visibility = FarmSettings.COST_VISIBILITY_FULL
        self.settings.save(update_fields=["mode", "fixed_asset_mode", "cost_visibility"])
        path = reverse("assets-capitalize", kwargs={"pk": self.solar_asset.pk})

        response = self.client.post(
            path,
            {
                "capitalized_value": "150000.00",
                "reason": "initial capitalization",
                "ref_id": "FA-1",
                "effective_date": "2026-01-15",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="asset-capitalize-1",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                object_id=str(self.solar_asset.pk),
                account_code=FinancialLedger.ACCOUNT_FIXED_ASSET,
                debit="150000.00",
            ).exists()
        )
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                object_id=str(self.solar_asset.pk),
                account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
                credit="150000.00",
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="FIXED_ASSET_CAPITALIZE",
                object_id=str(self.solar_asset.pk),
            ).exists()
        )
        self.assertTrue(
            IdempotencyRecord.objects.filter(
                user=self.user,
                key="asset-capitalize-1",
                path=path,
                status=IdempotencyRecord.STATUS_SUCCEEDED,
            ).exists()
        )

    def test_dispose_action_posts_ledger_audit_and_idempotency(self):
        self._ensure_open_period()
        self.settings.mode = FarmSettings.MODE_STRICT
        self.settings.fixed_asset_mode = FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION
        self.settings.cost_visibility = FarmSettings.COST_VISIBILITY_FULL
        self.settings.save(update_fields=["mode", "fixed_asset_mode", "cost_visibility"])
        path = reverse("assets-dispose", kwargs={"pk": self.tractor_asset.pk})

        response = self.client.post(
            path,
            {
                "proceeds_value": "25000.00",
                "reason": "disposed after replacement",
                "ref_id": "FA-2",
                "effective_date": "2026-01-20",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="asset-dispose-1",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                object_id=str(self.tractor_asset.pk),
                account_code=FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION,
                debit="10000.00",
            ).exists()
        )
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                object_id=str(self.tractor_asset.pk),
                account_code=FinancialLedger.ACCOUNT_FIXED_ASSET,
                credit="80000.00",
            ).exists()
        )
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                object_id=str(self.tractor_asset.pk),
                account_code=FinancialLedger.ACCOUNT_CASH_ON_HAND,
                debit="25000.00",
            ).exists()
        )
        self.assertTrue(
            FinancialLedger.objects.filter(
                farm=self.farm,
                object_id=str(self.tractor_asset.pk),
                account_code=FinancialLedger.ACCOUNT_ASSET_DISPOSAL_LOSS,
                debit="45000.00",
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="FIXED_ASSET_DISPOSE",
                object_id=str(self.tractor_asset.pk),
            ).exists()
        )
        self.assertTrue(
            IdempotencyRecord.objects.filter(
                user=self.user,
                key="asset-dispose-1",
                path=path,
                status=IdempotencyRecord.STATUS_SUCCEEDED,
            ).exists()
        )
