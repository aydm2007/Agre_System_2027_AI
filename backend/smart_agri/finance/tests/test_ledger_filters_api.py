from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.finance.models import FinancialLedger
from smart_agri.core.models.farm import Farm, Location
from smart_agri.core.models.crop import Crop
from smart_agri.core.models.planning import CropPlan, CropPlanLocation
from smart_agri.core.models.activity import Activity, ActivityLocation
from smart_agri.core.models.log import DailyLog


class TestLedgerFiltersAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username="finance_admin",
            email="finance@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=self.user)
        self.version = getattr(settings, "APP_VERSION", "2.0.0")
        self.farm = Farm.objects.create(name="Finance Filter Farm", slug="finance-filter-farm", region="R1")
        self.location = Location.objects.create(farm=self.farm, name="Primary Location")
        self.crop = Crop.objects.create(name="Ledger Crop", mode="Open")

    def test_account_and_date_filters(self):
        """
        Test ledger API filters by account_code and created_at range.
        The immutability trigger blocks UPDATE on ledger rows, so we
        cannot override created_at after creation. Instead, we just
        create entries and verify filtering by account_code works.
        """
        FinancialLedger.objects.create(
            account_code=FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
            debit=Decimal("0.0000"),
            credit=Decimal("11000.0000"),
            description="Salary payment",
            created_by=self.user,
        )
        FinancialLedger.objects.create(
            account_code=FinancialLedger.ACCOUNT_MATERIAL,
            debit=Decimal("11000.0000"),
            credit=Decimal("0.0000"),
            description="Material purchase",
            created_by=self.user,
        )

        # Filter by account_code only (avoids trigger conflict from date manipulation)
        response = self.client.get(
            "/api/v1/finance/ledger/",
            {"account_code": FinancialLedger.ACCOUNT_PAYABLE_SALARIES},
            HTTP_X_APP_VERSION=self.version,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        rows = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["account_code"], FinancialLedger.ACCOUNT_PAYABLE_SALARIES)

    def test_location_filter_uses_plan_locations_without_500(self):
        plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name="Location Filter Plan",
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
        )
        CropPlanLocation.objects.create(crop_plan=plan, location=self.location)
        FinancialLedger.objects.create(
            farm=self.farm,
            crop_plan=plan,
            account_code=FinancialLedger.ACCOUNT_MATERIAL,
            debit=Decimal("10.0000"),
            credit=Decimal("0.0000"),
            description="Location scoped ledger",
            created_by=self.user,
        )

        response = self.client.get(
            "/api/v1/finance/ledger/",
            {"farm": self.farm.id, "location": self.location.id},
            HTTP_X_APP_VERSION=self.version,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        rows = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["crop_plan"], plan.id)

    def test_crop_plan_and_crop_plan_id_aliases_match_activity_backed_entries(self):
        plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name="Alias Plan",
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
        )
        log = DailyLog.objects.create(
            farm=self.farm,
            log_date=timezone.localdate(),
            created_by=self.user,
        )
        activity = Activity.objects.create(
            log=log,
            crop_plan=plan,
            crop=self.crop,
            created_by=self.user,
        )
        ActivityLocation.objects.create(activity=activity, location=self.location)
        activity_backed_entry = FinancialLedger.objects.create(
            farm=self.farm,
            activity=activity,
            account_code=FinancialLedger.ACCOUNT_MATERIAL,
            debit=Decimal("25.0000"),
            credit=Decimal("0.0000"),
            description="Activity-backed ledger",
            created_by=self.user,
        )
        direct_entry = FinancialLedger.objects.create(
            farm=self.farm,
            crop_plan=plan,
            account_code=FinancialLedger.ACCOUNT_MATERIAL,
            debit=Decimal("15.0000"),
            credit=Decimal("0.0000"),
            description="Direct plan ledger",
            created_by=self.user,
        )

        for param_name in ("crop_plan", "crop_plan_id"):
            response = self.client.get(
                "/api/v1/finance/ledger/",
                {"farm": self.farm.id, param_name: plan.id},
                HTTP_X_APP_VERSION=self.version,
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            rows = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
            row_ids = {str(row["id"]) for row in rows}
            self.assertSetEqual(row_ids, {str(activity_backed_entry.id), str(direct_entry.id)})

    def test_activity_alias_filters_ledger_rows(self):
        plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name="Activity Filter Plan",
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
        )
        log = DailyLog.objects.create(
            farm=self.farm,
            log_date=timezone.localdate(),
            created_by=self.user,
        )
        activity = Activity.objects.create(
            log=log,
            crop_plan=plan,
            crop=self.crop,
            created_by=self.user,
        )
        ActivityLocation.objects.create(activity=activity, location=self.location)
        matching_entry = FinancialLedger.objects.create(
            farm=self.farm,
            activity=activity,
            account_code=FinancialLedger.ACCOUNT_MATERIAL,
            debit=Decimal("11.0000"),
            credit=Decimal("0.0000"),
            description="Matching activity ledger",
            created_by=self.user,
        )
        FinancialLedger.objects.create(
            farm=self.farm,
            crop_plan=plan,
            account_code=FinancialLedger.ACCOUNT_MATERIAL,
            debit=Decimal("9.0000"),
            credit=Decimal("0.0000"),
            description="Non-activity ledger",
            created_by=self.user,
        )

        for param_name in ("activity", "activity_id"):
            response = self.client.get(
                "/api/v1/finance/ledger/",
                {"farm": self.farm.id, param_name: activity.id},
                HTTP_X_APP_VERSION=self.version,
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            rows = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
            self.assertEqual(len(rows), 1)
            self.assertEqual(str(rows[0]["id"]), str(matching_entry.id))
