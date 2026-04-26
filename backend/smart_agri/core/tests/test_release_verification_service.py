import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from django.test import SimpleTestCase

from smart_agri.core.services.release_verification_service import (
    AxisDefinition,
    VerificationStep,
    build_axis_complete_steps,
    build_axis_results,
    build_release_gate_steps,
    build_static_steps,
    execute_suite,
)


class ReleaseVerificationServiceTests(SimpleTestCase):
    def test_execute_suite_writes_summary_and_copies_artifacts(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            artifact = repo_root / "backend" / "release_readiness_snapshot.json"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text('{"status": "ok"}', encoding="utf-8")

            summary = execute_suite(
                repo_root=repo_root,
                command_name="verify_static_v21",
                title="Static Verification",
                steps=[
                    VerificationStep(
                        key="pass_step",
                        label="Pass step",
                        group="static",
                        command=(sys.executable, "-c", "print('ok')"),
                    )
                ],
                artifact_paths=("backend/release_readiness_snapshot.json",),
            )

            self.assertEqual(summary["overall_status"], "PASS")
            self.assertTrue((repo_root / "docs" / "evidence" / "closure" / "latest" / "verify_static_v21" / "summary.json").exists())
            self.assertTrue((repo_root / "docs" / "evidence" / "closure" / "latest" / "verify_static_v21" / "artifacts" / "release_readiness_snapshot.json").exists())

    def test_execute_suite_marks_connection_errors_as_blocked(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            summary = execute_suite(
                repo_root=repo_root,
                command_name="verify_release_gate_v21",
                title="Release Gate",
                steps=[
                    VerificationStep(
                        key="blocked_step",
                        label="Blocked step",
                        group="runtime",
                        command=(sys.executable, "-c", "import sys; print('connection refused'); sys.exit(1)"),
                    )
                ],
            )

            self.assertEqual(summary["overall_status"], "BLOCKED")
            self.assertEqual(summary["steps"][0]["status"], "BLOCKED")

    def test_execute_suite_applies_env_overrides_with_suite_tmp_directory(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            summary = execute_suite(
                repo_root=repo_root,
                command_name="verify_axis_complete_v21",
                title="Axis Verification",
                steps=[
                    VerificationStep(
                        key="env_step",
                        label="Env step",
                        group="axis_frontend",
                        command=(
                            sys.executable,
                            "-c",
                            "import os; print(os.environ['PLAYWRIGHT_ARTIFACT_ROOT']); print(os.environ['STATIC_TAG'])",
                        ),
                        env_overrides=(("PLAYWRIGHT_ARTIFACT_ROOT", "{suite_tmp}"), ("STATIC_TAG", "ready")),
                    )
                ],
            )

            step = summary["steps"][0]
            self.assertEqual(summary["overall_status"], "PASS")
            self.assertEqual(step["env_overrides"]["STATIC_TAG"], "ready")
            artifact_root = Path(step["env_overrides"]["PLAYWRIGHT_ARTIFACT_ROOT"])
            self.assertTrue(artifact_root.exists())
            self.assertIn(str(repo_root / "docs" / "evidence" / "closure"), str(artifact_root))
            log_text = Path(step["log_path"]).read_text(encoding="utf-8")
            self.assertIn("env_overrides", log_text)
            self.assertIn("ready", log_text)

    def test_v21_step_builders_include_canonical_gates(self):
        repo_root = Path("C:/repo")
        static_keys = {step.key for step in build_static_steps(repo_root)}
        release_steps = {step.key: step for step in build_release_gate_steps(repo_root, skip_frontend=True)}
        axis_steps = {step.key: step for step in build_axis_complete_steps(repo_root, skip_frontend=False)}
        release_keys = set(release_steps)
        axis_keys = set(axis_steps)

        self.assertIn("decimal_mutations", static_keys)
        self.assertIn("service_layer_writes", static_keys)
        self.assertIn("float_guard_strict", release_keys)
        self.assertIn("backend_contract_asset_fuel_cash_tests", release_keys)
        self.assertIn("scan_pending_attachments", release_keys)
        self.assertIn("schema_detect_zombies", axis_keys)
        self.assertIn("axis_tenant_audit_variance_tests", axis_keys)
        self.assertIn("axis_governance_maintenance_dry_run", axis_keys)
        self.assertIn("--metadata-flag", release_steps["dispatch_outbox"].command)
        self.assertIn("seed_runtime_governance", release_steps["dispatch_outbox"].command)
        self.assertIn("--limit", release_steps["retry_dead_letters"].command)
        self.assertEqual(axis_steps["axis_playwright_daily_log"].env_overrides, (("PLAYWRIGHT_ARTIFACT_ROOT", "{suite_tmp}"),))
        self.assertIn("--reporter=line", axis_steps["axis_playwright_daily_log"].command)
        self.assertNotIn("--output=frontend/.pw-results-axis-daily-log", axis_steps["axis_playwright_daily_log"].command)

    def test_build_axis_results_marks_missing_steps_blocked(self):
        axis = AxisDefinition(
            number=1,
            key="schema_parity",
            title="Schema Parity",
            code_anchor="code.py",
            test_anchor="test.py",
            gate_anchor="gate",
            runtime_anchor="runtime",
            step_keys=("present_step", "missing_step"),
        )
        results = build_axis_results(
            axis_definitions=[axis],
            steps=[
                {
                    "key": "present_step",
                    "status": "PASS",
                    "label": "Present step",
                    "log_path": "log.txt",
                }
            ],
        )

        self.assertEqual(results[0]["status"], "BLOCKED")
        self.assertEqual(results[0]["missing_step_keys"], ["missing_step"])

    def test_execute_suite_writes_axis_summary(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            summary = execute_suite(
                repo_root=repo_root,
                command_name="verify_axis_complete_v21",
                title="Axis Verification",
                steps=[
                    VerificationStep(
                        key="axis_pass",
                        label="Axis pass",
                        group="axis_backend",
                        command=(sys.executable, "-c", "print('ok')"),
                    )
                ],
                axis_definitions=[
                    AxisDefinition(
                        number=1,
                        key="axis_one",
                        title="Axis One",
                        code_anchor="code.py",
                        test_anchor="test.py",
                        gate_anchor="gate",
                        runtime_anchor="runtime",
                        step_keys=("axis_pass",),
                    )
                ],
            )

            self.assertEqual(summary["axis_overall_status"], "PASS")
            latest_summary = repo_root / "docs" / "evidence" / "closure" / "latest" / "verify_axis_complete_v21" / "summary.md"
            text = latest_summary.read_text(encoding="utf-8")
            self.assertIn("## Axis Summary", text)
            self.assertIn("Axis One", text)

    def test_execute_suite_records_fallback_when_latest_mirror_is_locked(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            original_write_text = Path.write_text

            def guarded_write_text(path_obj, data, *args, **kwargs):
                target = str(path_obj)
                if target.endswith(str(Path("latest") / "verify_axis_complete_v21" / "logs" / "pass_step.log")):
                    raise PermissionError("locked latest step log")
                if target.endswith(str(Path("latest") / "verify_axis_complete_v21" / "summary.md")):
                    raise PermissionError("locked latest summary")
                return original_write_text(path_obj, data, *args, **kwargs)

            with mock.patch("pathlib.Path.write_text", autospec=True, side_effect=guarded_write_text):
                summary = execute_suite(
                    repo_root=repo_root,
                    command_name="verify_axis_complete_v21",
                    title="Axis Verification",
                    steps=[
                        VerificationStep(
                            key="pass_step",
                            label="Pass step",
                            group="axis_backend",
                            command=(sys.executable, "-c", "print('ok')"),
                        )
                    ],
                )

            self.assertEqual(summary["overall_status"], "PASS")
            self.assertIn("latest_sync_warnings", summary)
            self.assertEqual(len(summary["latest_sync_warnings"]), 2)
            self.assertIn(".fallback-", summary["steps"][0]["latest_log_path"])
            suite_summary = repo_root / "docs" / "evidence" / "closure"
            summary_json = next(suite_summary.glob("*/verify_axis_complete_v21/summary.json"))
            summary_text = summary_json.read_text(encoding="utf-8")
            self.assertIn("DEGRADED_LATEST_MIRROR", summary_text)
