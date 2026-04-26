from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase, override_settings

from smart_agri.core.models.farm import Farm
from smart_agri.core.uat.al_husseiniya import (
    AL_HUSSEINIYA_FARM_SLUG,
    run_al_husseiniya_uat,
    seed_al_husseiniya_uat,
)


class AlHusseiniyaUATTests(TestCase):
    def test_seed_al_husseiniya_uat_is_idempotent(self):
        first = seed_al_husseiniya_uat(clean=True)
        second = seed_al_husseiniya_uat(clean=False)

        self.assertEqual(first.farm.id, second.farm.id)
        self.assertEqual(first.farm.slug, AL_HUSSEINIYA_FARM_SLUG)
        self.assertEqual(first.governance.tier, Farm.TIER_MEDIUM)
        self.assertIn("mango_orchard_west", second.locations)

    @override_settings(MEDIA_ROOT="test_media_al_husseiniya")
    def test_run_al_husseiniya_uat_writes_artifacts(self):
        with TemporaryDirectory() as tmpdir:
            report = run_al_husseiniya_uat(artifact_root=tmpdir, clean_seed=True)

            self.assertEqual(report["overall_status"], "PASS")
            self.assertEqual(len(report["phases"]), 14)
            self.assertTrue((Path(tmpdir) / "summary.json").exists())
            self.assertTrue((Path(tmpdir) / "summary.md").exists())
            self.assertTrue((Path(tmpdir) / "logs" / "phases.json").exists())

    @override_settings(MEDIA_ROOT="test_media_al_husseiniya_cmd")
    def test_management_commands_execute(self):
        with TemporaryDirectory() as tmpdir:
            call_command("seed_al_husseiniya_uat", "--clean")
            call_command("run_al_husseiniya_uat", "--artifact-root", tmpdir)
            self.assertTrue(Farm.objects.filter(slug=AL_HUSSEINIYA_FARM_SLUG).exists())
            self.assertTrue((Path(tmpdir) / "summary.json").exists())
