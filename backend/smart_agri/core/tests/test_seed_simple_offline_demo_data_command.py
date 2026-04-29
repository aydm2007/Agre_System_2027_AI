from django.core.management import call_command
from django.test import TestCase

from smart_agri.core.models import Activity, DailyLog, Farm, OfflineSyncQuarantine, SyncConflictDLQ, SyncRecord
from smart_agri.core.models.settings import FarmSettings


class SeedSimpleOfflineDemoDataCommandTests(TestCase):
    def test_command_seeds_repeatable_simple_offline_demo_scope(self):
        call_command("seed_simple_offline_demo_data", reset_demo=True, with_offline_fixtures=True, verbosity=0)
        call_command("seed_simple_offline_demo_data", reset_demo=True, with_offline_fixtures=True, verbosity=0)

        farm = Farm.objects.get(slug="simple-offline-demo-farm")
        self.assertEqual(farm.operational_mode, FarmSettings.MODE_SIMPLE)
        self.assertEqual(farm.settings.mode, FarmSettings.MODE_SIMPLE)
        self.assertTrue(farm.settings.enable_offline_conflict_resolution)

        self.assertTrue(DailyLog.objects.filter(farm=farm, mobile_request_id="simple-offline-demo-log-1").exists())
        self.assertTrue(Activity.objects.filter(log__farm=farm, task__name="All Smart Cards Demo").exists())
        self.assertEqual(
            SyncRecord.objects.filter(farm=farm, reference__startswith="demo-offline-").count(),
            4,
        )
        self.assertEqual(
            SyncConflictDLQ.objects.filter(farm=farm, idempotency_key="demo-dead-letter-retryable").count(),
            1,
        )
        self.assertEqual(
            OfflineSyncQuarantine.objects.filter(farm=farm, idempotency_key="demo-mode-switch-quarantine").count(),
            1,
        )
