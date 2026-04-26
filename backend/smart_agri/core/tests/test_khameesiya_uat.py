from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.utils import timezone
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from smart_agri.core.models.farm import Farm
from smart_agri.core.api.serializers.activity import ActivitySerializer
from smart_agri.core.api.serializers.daily_log import DailyLogSerializer
from smart_agri.core.uat.khameesiya import (
    KHAMEESIYA_FARM_SLUG,
    run_khameesiya_uat,
    seed_khameesiya_uat,
)


class KhameesiyaUATTests(TestCase):
    def test_seed_khameesiya_uat_is_idempotent(self):
        first = seed_khameesiya_uat(clean=True)
        second = seed_khameesiya_uat(clean=False)

        self.assertEqual(first.farm.id, second.farm.id)
        self.assertEqual(first.farm.slug, KHAMEESIYA_FARM_SLUG)
        self.assertEqual(first.settings.approval_profile, "strict_finance")
        self.assertIn("tomato", second.plans)
        self.assertIn("mango", second.plans)
        self.assertIn("banana", second.plans)

    @override_settings(MEDIA_ROOT="test_media_khameesiya")
    def test_run_khameesiya_uat_writes_summary(self):
        with TemporaryDirectory() as tmpdir:
            report = run_khameesiya_uat(artifact_root=tmpdir, clean_seed=True)

            self.assertIn("overall_status", report)
            self.assertEqual(report["overall_status"], "PASS")
            self.assertEqual(len(report["phases"]), 12)
            self.assertTrue((Path(tmpdir) / "summary.json").exists())
            self.assertTrue((Path(tmpdir) / "summary.md").exists())
            self.assertTrue((Path(tmpdir) / "before_report.json").exists())

    def test_khameesiya_machinery_activity_costing_uses_compatible_currency_fallback(self):
        ctx = seed_khameesiya_uat(clean=True)
        factory = APIRequestFactory()
        request = factory.post("/api/v1/activities/")
        request.user = ctx.users["field_operator"]

        log_serializer = DailyLogSerializer(
            data={
                "farm": ctx.farm.id,
                "log_date": timezone.localdate().isoformat(),
            },
            context={"request": request},
        )
        self.assertTrue(log_serializer.is_valid(), log_serializer.errors)
        log = log_serializer.save(
            created_by=ctx.users["field_operator"],
            updated_by=ctx.users["field_operator"],
        )

        serializer = ActivitySerializer(
            data={
                "log_id": log.id,
                "crop_id": ctx.plans["tomato"].crop_id,
                "task_id": ctx.tasks["tomato_service"].id,
                "location_ids": [ctx.locations["tomato_field"].id],
                "asset_id": ctx.assets["tractor"].id,
                "machine_hours": 1,
                "items": [],
                "employees": [],
                "employees_payload": [],
                "notes": "compat currency fallback",
            },
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        activity = serializer.save()

        self.assertEqual(activity.cost_machinery, activity.cost_total)
        self.assertEqual(activity.cost_snapshots.filter(deleted_at__isnull=True).count(), 1)
        self.assertEqual(activity.cost_snapshots.first().currency, "YER")

    @override_settings(MEDIA_ROOT="test_media_khameesiya_cmd")
    def test_management_commands_execute(self):
        with TemporaryDirectory() as tmpdir:
            call_command("seed_khameesiya_uat", "--clean")
            call_command("run_khameesiya_uat", "--artifact-root", tmpdir)
            self.assertTrue(Farm.objects.filter(slug=KHAMEESIYA_FARM_SLUG).exists())
            self.assertTrue((Path(tmpdir) / "summary.json").exists())
