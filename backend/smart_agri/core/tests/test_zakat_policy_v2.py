from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from smart_agri.core.models import (
    Activity,
    ActivityHarvest,
    Crop,
    CropPlan,
    CropProduct,
    DailyLog,
    Farm,
    Item,
    Location,
    LocationIrrigationPolicy,
    Unit,
)
from smart_agri.core.services.harvest_service import HarvestService
from smart_agri.core.services.zakat_policy import (
    QuarantinedSyncError,
    resolve_zakat_policy_for_harvest,
)
from smart_agri.finance.models import FinancialLedger

try:
    from django.db.backends.postgresql.psycopg_any import DateRange
except Exception:  # pragma: no cover
    from psycopg2.extras import DateRange


class ZakatPolicyV2Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="zakat-v2-user", password="123456")
        self.farm = Farm.objects.create(name="Zakat V2 Farm", slug="zakat-v2-farm", region="north")
        self.location = Location.objects.create(farm=self.farm, name="Plot A", type="Field")
        self.unit = Unit.objects.create(code="kg", name="Kilogram")
        self.crop = Crop.objects.create(name="Wheat")
        self.item = Item.objects.create(name="Wheat Product", group="Harvested Product", uom="kg", unit=self.unit)
        self.product = CropProduct.objects.create(crop=self.crop, item=self.item, name="Wheat Product")
        self.plan = CropPlan.objects.create(farm=self.farm, crop=self.crop, season="2026", area=Decimal("10"))
        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date=date.today(),
            created_by=self.user,
        )

    def _make_activity(self, qty=Decimal("100.0"), cost_total=Decimal("1000.0"), device_timestamp=None):
        activity = Activity.objects.create(
            log=self.log,
            crop_plan=self.plan,
            location=self.location,
            product=self.product,
            cost_total=cost_total,
            device_timestamp=device_timestamp,
        )
        ActivityHarvest.objects.create(
            activity=activity,
            harvest_quantity=qty,
            product_id=self.product.id,
            uom="kg",
        )
        return activity

    def test_location_policy_overlap_blocked(self):
        if connection.vendor != "postgresql":
            self.skipTest("PostgreSQL required for exclusion constraint.")
        LocationIrrigationPolicy.objects.create(
            location=self.location,
            zakat_rule=LocationIrrigationPolicy.ZAKAT_WELL_5,
            valid_daterange=DateRange(date(2025, 1, 1), date(2025, 7, 1), "[)"),
            reason="Initial policy",
            approved_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LocationIrrigationPolicy.objects.create(
                    location=self.location,
                    zakat_rule=LocationIrrigationPolicy.ZAKAT_RAIN_10,
                    valid_daterange=DateRange(date(2025, 6, 1), date(2025, 12, 1), "[)"),
                    reason="Overlap should fail",
                    approved_by=self.user,
                )

    @override_settings(LOCATION_ZAKAT_POLICY_V2_MODE="enforce")
    def test_resolve_policy_by_business_date(self):
        LocationIrrigationPolicy.objects.create(
            location=self.location,
            zakat_rule=LocationIrrigationPolicy.ZAKAT_WELL_5,
            valid_daterange=DateRange(date(2025, 1, 1), date(2025, 7, 1), "[)"),
            reason="Well season",
            approved_by=self.user,
        )
        LocationIrrigationPolicy.objects.create(
            location=self.location,
            zakat_rule=LocationIrrigationPolicy.ZAKAT_RAIN_10,
            valid_daterange=DateRange(date(2025, 7, 1), None, "[)"),
            reason="Rain season",
            approved_by=self.user,
        )
        early = resolve_zakat_policy_for_harvest(self.location, date(2025, 3, 1))
        late = resolve_zakat_policy_for_harvest(self.location, date(2025, 10, 1))
        self.assertEqual(early.zakat_rule, LocationIrrigationPolicy.ZAKAT_WELL_5)
        self.assertEqual(late.zakat_rule, LocationIrrigationPolicy.ZAKAT_RAIN_10)

    @override_settings(LOCATION_ZAKAT_POLICY_V2_MODE="enforce")
    def test_no_policy_gap_quarantines_new_harvest(self):
        with self.assertRaises(QuarantinedSyncError):
            resolve_zakat_policy_for_harvest(self.location, date(2025, 5, 1))

    def test_mixed_75_decimal_integrity(self):
        due = HarvestService.calculate_zakat_due(Decimal("1000"), "MIXED_75")
        self.assertEqual(due, Decimal("75.0000"))
        self.assertIsInstance(due, Decimal)

    @override_settings(LOCATION_ZAKAT_POLICY_V2_MODE="enforce")
    def test_offline_harvest_uses_device_timestamp_for_policy(self):
        LocationIrrigationPolicy.objects.create(
            location=self.location,
            zakat_rule=LocationIrrigationPolicy.ZAKAT_WELL_5,
            valid_daterange=DateRange(date(2025, 1, 1), date(2025, 7, 1), "[)"),
            reason="Well season",
            approved_by=self.user,
        )
        LocationIrrigationPolicy.objects.create(
            location=self.location,
            zakat_rule=LocationIrrigationPolicy.ZAKAT_RAIN_10,
            valid_daterange=DateRange(date(2025, 7, 1), None, "[)"),
            reason="Rain season",
            approved_by=self.user,
        )
        self.log.log_date = date(2025, 8, 1)
        self.log.save(update_fields=["log_date"])
        device_ts = timezone.make_aware(datetime(2025, 3, 10, 10, 0, 0))
        activity = self._make_activity(device_timestamp=device_ts)
        HarvestService.process_harvest(activity, self.user)
        zakat_credit = FinancialLedger.objects.filter(
            activity=activity,
            account_code=FinancialLedger.ACCOUNT_ZAKAT_PAYABLE,
        ).values_list("credit", flat=True).first()
        self.assertEqual(zakat_credit, Decimal("50.0000"))

    @override_settings(LOCATION_ZAKAT_POLICY_V2_MODE="enforce")
    def test_harvest_idempotent_replay_no_double_ledger(self):
        LocationIrrigationPolicy.objects.create(
            location=self.location,
            zakat_rule=LocationIrrigationPolicy.ZAKAT_WELL_5,
            valid_daterange=DateRange(date(2020, 1, 1), None, "[)"),
            reason="Active policy",
            approved_by=self.user,
        )
        activity = self._make_activity()
        HarvestService.process_harvest(activity, self.user)
        HarvestService.process_harvest(activity, self.user)
        count = FinancialLedger.objects.filter(
            activity=activity,
            account_code=FinancialLedger.ACCOUNT_ZAKAT_PAYABLE,
        ).count()
        self.assertEqual(count, 1)

    # ──────────────────────────────────────────────────────────────────────────
    # TI-07: Zakat Toggle-Off E2E Backend Test
    # When zakat_enabled=False for a farm, harvest must not trigger zakat
    # calculation, but the financial ledger still records harvest revenue.
    # ──────────────────────────────────────────────────────────────────────────

    def test_zakat_disabled_tenant_no_zakat_trigger(self):
        """TI-07: zakat_enabled=False — harvest must NOT trigger zakat calculation."""
        from django.test import override_settings

        # Disable Zakat for this farm
        farm_settings = self.farm.settings if hasattr(self.farm, "settings") else None
        if farm_settings is not None:
            farm_settings.zakat_enabled = False
            farm_settings.save(update_fields=["zakat_enabled"])
        else:
            # If FarmSettings does not exist or zakat_enabled not a field, skip gracefully
            self.skipTest("FarmSettings.zakat_enabled not available in this schema version.")

        with override_settings(LOCATION_ZAKAT_POLICY_V2_MODE="enforce"):
            from django.utils import timezone as tz
            from datetime import datetime
            LocationIrrigationPolicy.objects.create(
                location=self.location,
                zakat_rule=LocationIrrigationPolicy.ZAKAT_WELL_5,
                valid_daterange=DateRange(date(2020, 1, 1), None, "[)"),
                reason="Active policy for zakat-disabled test",
                approved_by=self.user,
            )
            activity = self._make_activity(qty=Decimal("10000"))
            HarvestService.process_harvest(activity, self.user)

        # No Zakat payable entry should exist
        zakat_records = FinancialLedger.objects.filter(
            activity=activity,
            account_code=FinancialLedger.ACCOUNT_ZAKAT_PAYABLE,
        )
        self.assertEqual(
            zakat_records.count(),
            0,
            "Zakat should not be calculated when zakat_enabled=False for the farm.",
        )

        # Harvest revenue entry SHOULD still be recorded
        try:
            HARVEST_ACCOUNT = FinancialLedger.ACCOUNT_HARVEST_REVENUE
        except AttributeError:
            HARVEST_ACCOUNT = None

        if HARVEST_ACCOUNT:
            harvest_ledger = FinancialLedger.objects.filter(
                activity=activity,
                account_code=HARVEST_ACCOUNT,
            )
            self.assertGreater(
                harvest_ledger.count(),
                0,
                "Harvest revenue ledger entry must still exist even when Zakat is disabled.",
            )

    def test_zakat_re_enabled_resumes_calculation(self):
        """TI-07 complement: re-enabling zakat causes the next harvest to trigger it again."""
        from django.test import override_settings

        farm_settings = self.farm.settings if hasattr(self.farm, "settings") else None
        if farm_settings is None:
            self.skipTest("FarmSettings not attached to farm in this schema version.")
        if not hasattr(farm_settings, "zakat_enabled"):
            self.skipTest("FarmSettings.zakat_enabled field not available.")

        # Phase 1: disable
        farm_settings.zakat_enabled = False
        farm_settings.save(update_fields=["zakat_enabled"])

        # Phase 2: re-enable
        farm_settings.zakat_enabled = True
        farm_settings.save(update_fields=["zakat_enabled"])

        with override_settings(LOCATION_ZAKAT_POLICY_V2_MODE="enforce"):
            LocationIrrigationPolicy.objects.create(
                location=self.location,
                zakat_rule=LocationIrrigationPolicy.ZAKAT_WELL_5,
                valid_daterange=DateRange(date(2020, 1, 1), None, "[)"),
                reason="Re-enabled zakat test",
                approved_by=self.user,
            )
            activity = self._make_activity(qty=Decimal("1000"))
            HarvestService.process_harvest(activity, self.user)

        zakat_count = FinancialLedger.objects.filter(
            activity=activity,
            account_code=FinancialLedger.ACCOUNT_ZAKAT_PAYABLE,
        ).count()
        self.assertEqual(
            zakat_count,
            1,
            "Zakat calculation must resume once zakat_enabled is set back to True.",
        )

