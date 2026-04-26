from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase, override_settings

from smart_agri.core.uat.rabouia_sarima import (
    DEFAULT_PASSWORD,
    RABOUIA_FARM_SLUG,
    SARIMA_FARM_SLUG,
    run_rabouia_sarima_uat,
    seed_rabouia_uat,
    seed_sarima_uat,
)


class RabouiaSarimaUATTests(TestCase):
    def test_seed_commands_are_idempotent(self):
        rab_first = seed_rabouia_uat(clean=True)
        rab_second = seed_rabouia_uat(clean=False)
        sar_first = seed_sarima_uat(clean=True)
        sar_second = seed_sarima_uat(clean=False)

        self.assertEqual(rab_first.farm.id, rab_second.farm.id)
        self.assertEqual(rab_first.farm.slug, RABOUIA_FARM_SLUG)
        self.assertEqual(rab_first.settings.mode, "SIMPLE")
        self.assertEqual(sar_first.farm.id, sar_second.farm.id)
        self.assertEqual(sar_first.farm.slug, SARIMA_FARM_SLUG)
        self.assertEqual(sar_first.settings.mode, "STRICT")
        self.assertTrue(rab_second.users["system_admin"].check_password(DEFAULT_PASSWORD))
        self.assertTrue(sar_second.users["system_admin"].check_password(DEFAULT_PASSWORD))

    @override_settings(MEDIA_ROOT="test_media_rabouia_sarima")
    def test_run_rabouia_sarima_uat_writes_expected_artifacts(self):
        with TemporaryDirectory() as tmpdir:
            report = run_rabouia_sarima_uat(artifact_root=tmpdir, clean_seed=True)

            self.assertEqual(report["overall_status"], "PASS")
            self.assertEqual(len(report["phases"]), 19)
            self.assertIn("after_scorecard", report)
            self.assertIn("improvements", report)
            self.assertTrue((Path(tmpdir) / "summary.json").exists())
            self.assertTrue((Path(tmpdir) / "summary.md").exists())
            self.assertTrue((Path(tmpdir) / "before_report.json").exists())
            self.assertTrue((Path(tmpdir) / "before_report.md").exists())
            self.assertTrue((Path(tmpdir) / "logs" / "phases.json").exists())
            self.assertIn("الربوعية", (Path(tmpdir) / "summary.md").read_text(encoding="utf-8"))
            self.assertIn("الصارمة", (Path(tmpdir) / "summary.md").read_text(encoding="utf-8"))

    @override_settings(MEDIA_ROOT="test_media_rabouia_sarima_rerun")
    def test_run_rabouia_sarima_uat_is_safe_on_repeated_clean_seed_runs(self):
        with TemporaryDirectory() as tmpdir:
            first_dir = Path(tmpdir) / "first"
            second_dir = Path(tmpdir) / "second"

            first = run_rabouia_sarima_uat(artifact_root=first_dir, clean_seed=True)
            second = run_rabouia_sarima_uat(artifact_root=second_dir, clean_seed=True)

            self.assertEqual(first["overall_status"], "PASS")
            self.assertEqual(second["overall_status"], "PASS")
            self.assertEqual(first["strict_summary_score"], 100.0)
            self.assertEqual(second["strict_summary_score"], 100.0)
            self.assertTrue((second_dir / "summary.json").exists())

    @override_settings(MEDIA_ROOT="test_media_rabouia_sarima_cmd")
    def test_management_commands_execute(self):
        with TemporaryDirectory() as tmpdir:
            call_command("seed_rabouia_uat", "--clean")
            call_command("seed_sarima_uat", "--clean")
            call_command("run_rabouia_sarima_uat", "--artifact-root", tmpdir)
            self.assertTrue((Path(tmpdir) / "summary.json").exists())
    
    @override_settings(MEDIA_ROOT="test_media_rabouia_sarima_cmd_rerun")
    def test_management_command_is_safe_on_repeated_clean_seed_runs(self):
        with TemporaryDirectory() as tmpdir:
            first_dir = Path(tmpdir) / "first"
            second_dir = Path(tmpdir) / "second"

            call_command("run_rabouia_sarima_uat", "--artifact-root", str(first_dir), "--clean-seed")
            call_command("run_rabouia_sarima_uat", "--artifact-root", str(second_dir), "--clean-seed")

            self.assertTrue((first_dir / "summary.json").exists())
            self.assertTrue((second_dir / "summary.json").exists())
