from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Asset, AuditLog, DailyLog, Farm, FuelConsumptionAlert, IdempotencyRecord, Supervisor
from smart_agri.core.models.settings import FarmSettings
from smart_agri.finance.models import FinancialLedger, FiscalPeriod, FiscalYear
from smart_agri.inventory.models import FuelLog, TankCalibration


class FuelReconciliationDashboardAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("fuel_manager", password="pass", is_staff=True, is_superuser=True)
        self.farm = Farm.objects.create(name="Fuel Farm", slug="fuel-farm", region="A")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role="Manager")
        self.supervisor = Supervisor.objects.create(farm=self.farm, name="Fuel Supervisor", code="SUP-FUEL")
        self.settings = FarmSettings.objects.create(
            farm=self.farm,
            mode=FarmSettings.MODE_SIMPLE,
            cost_visibility=FarmSettings.COST_VISIBILITY_SUMMARIZED,
            variance_behavior=FarmSettings.VARIANCE_BEHAVIOR_WARN,
            treasury_visibility=FarmSettings.TREASURY_VISIBILITY_HIDDEN,
        )
        self.tank = Asset.objects.create(
            farm=self.farm,
            category="Fuel",
            asset_type="tank",
            code="TNK-1",
            name="Diesel Tank 1",
        )
        self.machine = Asset.objects.create(
            farm=self.farm,
            category="Machinery",
            asset_type="tractor",
            code="TR-1",
            name="Field Tractor",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _create_log(self, reading_date=None, start="100.00", end="90.00"):
        if reading_date is None:
            reading_date = timezone.now()
        return FuelLog.objects.create(
            farm=self.farm,
            asset_tank=self.tank,
            supervisor=self.supervisor,
            reading_date=reading_date,
            measurement_method=FuelLog.MEASUREMENT_METHOD_DIPSTICK,
            reading_start_cm=Decimal(start),
            reading_end_cm=Decimal(end),
        )

    def _ensure_open_period(self, target_date):
        fiscal_year = FiscalYear.objects.create(
            farm=self.farm,
            year=target_date.year,
            start_date=target_date.replace(month=1, day=1),
            end_date=target_date.replace(month=12, day=31),
        )
        FiscalPeriod.objects.create(
            fiscal_year=fiscal_year,
            month=target_date.month,
            start_date=target_date.replace(day=1),
            end_date=target_date.replace(day=28),
            status=FiscalPeriod.STATUS_OPEN,
            is_closed=False,
        )

    def test_dashboard_flags_missing_calibration_and_machine_link(self):
        fuel_log = FuelLog(
            farm=self.farm,
            asset_tank=self.tank,
            supervisor=self.supervisor,
            reading_date=timezone.now(),
            measurement_method=FuelLog.MEASUREMENT_METHOD_COUNTER,
            reading_start_cm=Decimal("25.00"),
            reading_end_cm=Decimal("20.00"),
            liters_consumed=Decimal("5.0000"),
        )
        FuelLog.objects.bulk_create([fuel_log])
        fuel_log = FuelLog.objects.get(farm=self.farm, asset_tank=self.tank)

        response = self.client.get(reverse("fuel-reconciliation-list"), {"farm_id": self.farm.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["id"], fuel_log.id)
        self.assertTrue(row["flags"]["missing_calibration"])
        self.assertTrue(row["flags"]["no_machine_link"])
        self.assertEqual(row["variance_severity"], "warning")
        self.assertEqual(response.data["summary"]["missing_calibration_logs"], 1)

    def test_dashboard_reflects_warning_and_strict_policy(self):
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("90.00"), liters_volume=Decimal("90.0000"))
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("100.00"), liters_volume=Decimal("100.0000"))
        fuel_log = self._create_log()
        daily_log = DailyLog.objects.create(
            farm=self.farm,
            supervisor=self.supervisor,
            log_date=fuel_log.reading_date.date(),
            fuel_alert_status=DailyLog.FUEL_ALERT_STATUS_WARNING,
        )
        FuelConsumptionAlert.objects.create(
            log=daily_log,
            asset=self.machine,
            machine_hours=Decimal("1.00"),
            actual_liters=Decimal("10.0000"),
            expected_liters=Decimal("8.0000"),
            deviation_pct=Decimal("25.00"),
            status=FuelConsumptionAlert.STATUS_WARNING,
            note="warning variance",
        )
        self.settings.mode = FarmSettings.MODE_STRICT
        self.settings.cost_visibility = FarmSettings.COST_VISIBILITY_FULL
        self.settings.treasury_visibility = FarmSettings.TREASURY_VISIBILITY_VISIBLE
        self.settings.save(update_fields=["mode", "cost_visibility", "treasury_visibility"])

        response = self.client.get(reverse("fuel-reconciliation-list"), {"farm_id": self.farm.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.data["results"][0]
        self.assertEqual(row["cost_display_mode"], FarmSettings.COST_VISIBILITY_FULL)
        self.assertEqual(row["visibility_level"], "full_erp")
        self.assertTrue(row["flags"]["warning_variance"])
        self.assertEqual(row["reconciliation_state"], "pending_review")
        self.assertEqual(row["expected_liters"], "8.0000")
        self.assertEqual(response.data["summary"]["warning_logs"], 1)

    def test_dashboard_filters_by_tank_and_detects_critical_missing_benchmark(self):
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("70.00"), liters_volume=Decimal("70.0000"))
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("80.00"), liters_volume=Decimal("80.0000"))
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("100.00"), liters_volume=Decimal("100.0000"))
        other_tank = Asset.objects.create(
            farm=self.farm,
            category="Fuel",
            asset_type="tank",
            code="TNK-2",
            name="Diesel Tank 2",
        )
        TankCalibration.objects.create(asset=other_tank, cm_reading=Decimal("95.00"), liters_volume=Decimal("95.0000"))
        TankCalibration.objects.create(asset=other_tank, cm_reading=Decimal("80.00"), liters_volume=Decimal("80.0000"))
        TankCalibration.objects.create(asset=other_tank, cm_reading=Decimal("100.00"), liters_volume=Decimal("100.0000"))
        primary_log = self._create_log(reading_date=timezone.now() - timedelta(hours=2), start="100.00", end="70.00")
        FuelLog.objects.create(
            farm=self.farm,
            asset_tank=other_tank,
            supervisor=self.supervisor,
            reading_date=timezone.now() - timedelta(hours=1),
            measurement_method=FuelLog.MEASUREMENT_METHOD_DIPSTICK,
            reading_start_cm=Decimal("100.00"),
            reading_end_cm=Decimal("95.00"),
        )
        daily_log = DailyLog.objects.create(
            farm=self.farm,
            supervisor=self.supervisor,
            log_date=primary_log.reading_date.date(),
            fuel_alert_status=DailyLog.FUEL_ALERT_STATUS_CRITICAL,
        )
        FuelConsumptionAlert.objects.create(
            log=daily_log,
            asset=self.machine,
            machine_hours=Decimal("2.00"),
            actual_liters=Decimal("30.0000"),
            expected_liters=Decimal("0.0000"),
            deviation_pct=Decimal("0.00"),
            status=FuelConsumptionAlert.STATUS_CRITICAL,
            note="Field Tractor: missing fuel consumption benchmark.",
        )

        response = self.client.get(
            reverse("fuel-reconciliation-list"),
            {"farm_id": self.farm.id, "tank": self.tank.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["tank_id"], self.tank.id)
        self.assertTrue(row["flags"]["missing_benchmark"])
        self.assertTrue(row["flags"]["critical_variance"])
        self.assertEqual(row["variance_severity"], "critical")
        self.assertEqual(response.data["summary"]["critical_logs"], 1)

    def test_post_reconciliation_rejects_simple_mode_even_for_finance_manager(self):
        membership = FarmMembership.objects.get(user=self.user, farm=self.farm)
        membership.role = "Ø§Ù„Ù…Ø¯ÙŠØ± Ø§Ù„Ù…Ø§Ù„ÙŠ Ù„Ù„Ù…Ø²Ø±Ø¹Ø©"
        membership.save(update_fields=["role"])
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("90.00"), liters_volume=Decimal("90.0000"))
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("100.00"), liters_volume=Decimal("100.0000"))
        fuel_log = self._create_log()
        daily_log = DailyLog.objects.create(
            farm=self.farm,
            supervisor=self.supervisor,
            log_date=fuel_log.reading_date.date(),
            fuel_alert_status=DailyLog.FUEL_ALERT_STATUS_WARNING,
        )
        FuelConsumptionAlert.objects.create(
            log=daily_log,
            asset=self.machine,
            machine_hours=Decimal("1.00"),
            actual_liters=Decimal("10.0000"),
            expected_liters=Decimal("8.0000"),
            deviation_pct=Decimal("25.00"),
            status=FuelConsumptionAlert.STATUS_WARNING,
            note="warning variance",
        )

        response = self.client.post(
            reverse("fuel-reconciliation-post-reconciliation"),
            {
                "daily_log_id": daily_log.id,
                "fuel_log_id": fuel_log.id,
                "reason": "approve attempt",
                "ref_id": "FR-1",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="fuel-simple-denied",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("STRICT", response.data["detail"])

    def test_post_reconciliation_requires_idempotency_key(self):
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("90.00"), liters_volume=Decimal("90.0000"))
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("100.00"), liters_volume=Decimal("100.0000"))
        fuel_log = self._create_log()
        self._ensure_open_period(fuel_log.reading_date.date())
        daily_log = DailyLog.objects.create(
            farm=self.farm,
            supervisor=self.supervisor,
            log_date=fuel_log.reading_date.date(),
            fuel_alert_status=DailyLog.FUEL_ALERT_STATUS_WARNING,
        )
        FuelConsumptionAlert.objects.create(
            log=daily_log,
            asset=self.machine,
            machine_hours=Decimal("1.00"),
            actual_liters=Decimal("10.0000"),
            expected_liters=Decimal("8.0000"),
            deviation_pct=Decimal("25.00"),
            status=FuelConsumptionAlert.STATUS_WARNING,
            note="warning variance",
        )
        self.settings.mode = FarmSettings.MODE_STRICT
        self.settings.save(update_fields=["mode"])

        response = self.client.post(
            reverse("fuel-reconciliation-post-reconciliation"),
            {
                "daily_log_id": daily_log.id,
                "fuel_log_id": fuel_log.id,
                "reason": "approve attempt",
                "ref_id": "FR-2",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("X-Idempotency-Key", response.json()["detail"])

    def test_post_reconciliation_strict_mode_posts_ledger_audit_and_idempotency(self):
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("90.00"), liters_volume=Decimal("90.0000"))
        TankCalibration.objects.create(asset=self.tank, cm_reading=Decimal("100.00"), liters_volume=Decimal("100.0000"))
        fuel_log = self._create_log()
        self._ensure_open_period(fuel_log.reading_date.date())
        daily_log = DailyLog.objects.create(
            farm=self.farm,
            supervisor=self.supervisor,
            log_date=fuel_log.reading_date.date(),
            fuel_alert_status=DailyLog.FUEL_ALERT_STATUS_WARNING,
        )
        FuelConsumptionAlert.objects.create(
            log=daily_log,
            asset=self.machine,
            machine_hours=Decimal("1.00"),
            actual_liters=Decimal("10.0000"),
            expected_liters=Decimal("8.0000"),
            deviation_pct=Decimal("25.00"),
            status=FuelConsumptionAlert.STATUS_WARNING,
            note="warning variance",
        )
        self.settings.mode = FarmSettings.MODE_STRICT
        self.settings.save(update_fields=["mode"])

        path = reverse("fuel-reconciliation-post-reconciliation")
        response = self.client.post(
            path,
            {
                "daily_log_id": daily_log.id,
                "fuel_log_id": fuel_log.id,
                "reason": "approved for posting",
                "ref_id": "FR-3",
            },
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="fuel-post-1",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "posted")
        self.assertEqual(
            FinancialLedger.objects.filter(
                farm=self.farm,
                object_id=str(fuel_log.id),
                account_code=FinancialLedger.ACCOUNT_FUEL_EXPENSE,
            ).count(),
            1,
        )
        self.assertEqual(
            FinancialLedger.objects.filter(
                farm=self.farm,
                object_id=str(fuel_log.id),
                account_code=FinancialLedger.ACCOUNT_FUEL_INVENTORY,
            ).count(),
            1,
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="FUEL_RECONCILIATION_POST",
                object_id=str(fuel_log.id),
            ).exists()
        )
        self.assertTrue(
            IdempotencyRecord.objects.filter(
                user=self.user,
                key="fuel-post-1",
                path=path,
                status=IdempotencyRecord.STATUS_SUCCEEDED,
            ).exists()
        )
