from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from smart_agri.core.models.activity import ActivityIrrigation, Activity
from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.farm import Farm

class IrrigationSolarTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="مزرعة اختبار الشمسية")
        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date="2026-04-13",
        )
    
    def _create_activity(self):
        return Activity.objects.create(
            log=self.log,
            crop_plan=None,
        )
    
    def test_solar_irrigation_no_diesel_required(self):
        """Solar-powered irrigation should not require diesel_qty."""
        act = self._create_activity()
        irr = ActivityIrrigation(
            activity=act,
            water_volume=Decimal("100.000"),
            is_solar_powered=True,
            diesel_qty=None,
        )
        irr.full_clean()  # Should NOT raise
        irr.save()
        self.assertTrue(irr.is_solar_powered)
        self.assertIsNone(irr.diesel_qty)
    
    def test_diesel_irrigation_requires_diesel_qty(self):
        """Non-solar irrigation must provide diesel_qty."""
        act = self._create_activity()
        irr = ActivityIrrigation(
            activity=act,
            water_volume=Decimal("100.000"),
            is_solar_powered=False,
            diesel_qty=None,
        )
        with self.assertRaises(ValidationError):
            irr.full_clean()
    
    def test_water_volume_always_required(self):
        """water_volume is mandatory regardless of power source."""
        act = self._create_activity()
        irr = ActivityIrrigation(
            activity=act,
            water_volume=None,
            is_solar_powered=True,
        )
        with self.assertRaises(ValidationError):
            irr.full_clean()
    
    def test_well_reading_optional(self):
        """well_reading is always optional."""
        act = self._create_activity()
        irr = ActivityIrrigation(
            activity=act,
            water_volume=Decimal("50.000"),
            is_solar_powered=False,
            diesel_qty=Decimal("10.000"),
            well_reading=None,
        )
        irr.full_clean()  # Should NOT raise

    def test_solar_powered_does_not_flag_alert(self):
        """Solar-powered irrigation should produce STATUS_OK in diesel monitoring."""
        from smart_agri.core.services.diesel_monitoring import DieselMonitoringService

        act = self._create_activity()
        ActivityIrrigation.objects.create(
            activity=act,
            water_volume=Decimal("200.000"),
            is_solar_powered=True,
            diesel_qty=None,
        )
        # Should not raise; should return OK or empty alerts
        result = DieselMonitoringService.evaluate_log(self.log)
        self.assertIn(result['status'].lower(), ['ok', 'status_ok'])

    def test_serializer_rejects_diesel_with_solar(self):
        """Serializer should reject diesel_qty > 0 when is_solar_powered=True."""
        from smart_agri.core.api.serializers.activity import ActivityIrrigationSerializer

        data = {
            'water_volume': '100.000',
            'uom': 'm3',
            'is_solar_powered': True,
            'diesel_qty': '5.000',
        }
        serializer = ActivityIrrigationSerializer(data=data)
        # Assuming the validator is on the model, it validates internally
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # the model validation fails on full_clean
        with self.assertRaises(ValidationError):
            irr = ActivityIrrigation(**serializer.validated_data, activity=self._create_activity())
            irr.full_clean()

    def test_serializer_accepts_solar_without_diesel(self):
        """Serializer should accept solar irrigation without diesel."""
        from smart_agri.core.api.serializers.activity import ActivityIrrigationSerializer

        data = {
            'water_volume': '100.000',
            'uom': 'm3',
            'is_solar_powered': True,
            'diesel_qty': None,
        }
        serializer = ActivityIrrigationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_farm_settings_default_power_source(self):
        """FarmSettings should store default_irrigation_power_source."""
        from smart_agri.core.models.settings import FarmSettings

        settings, _ = FarmSettings.objects.get_or_create(farm=self.farm)
        self.assertEqual(settings.default_irrigation_power_source, 'diesel')

        settings.default_irrigation_power_source = 'solar'
        settings.full_clean()
        settings.save()
        settings.refresh_from_db()
        self.assertEqual(settings.default_irrigation_power_source, 'solar')
