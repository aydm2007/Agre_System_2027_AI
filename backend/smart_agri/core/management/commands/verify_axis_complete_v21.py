from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from smart_agri.core.services.release_verification_service import (
    build_axis_complete_steps,
    build_axis_definitions,
    execute_suite,
    repo_root_from_backend_dir,
)


class Command(BaseCommand):
    help = "Run the canonical axis-complete V21 verification suite and write a unified axis evidence bundle."

    def add_arguments(self, parser):
        parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend focused proofs.")

    def handle(self, *args, **options):
        repo_root = repo_root_from_backend_dir(Path(settings.BASE_DIR))
        summary = execute_suite(
            repo_root=repo_root,
            command_name="verify_axis_complete_v21",
            title="V21 Axis-Complete Verification",
            steps=build_axis_complete_steps(repo_root, skip_frontend=options["skip_frontend"]),
            artifact_paths=(
                "backend/release_readiness_snapshot.json",
                "backend/release_readiness_snapshot.md",
                "backend/scripts/release_gate_float_check.txt",
            ),
            axis_definitions=build_axis_definitions(),
        )
        for axis in summary.get("axes", []):
            self.stdout.write(f"{axis['status']}: axis_{axis['number']} {axis['title']}")
        self.stdout.write(self.style.SUCCESS(f"evidence_dir={summary['suite_dir']}"))
        self.stdout.write(f"overall_status={summary['overall_status']}")
        self.stdout.write(f"axis_overall_status={summary.get('axis_overall_status', summary['overall_status'])}")
        if summary["overall_status"] != "PASS" or summary.get("axis_overall_status") != "PASS":
            raise CommandError(
                "verify_axis_complete_v21 incomplete: "
                f"status={summary['overall_status']} axis_status={summary.get('axis_overall_status')} "
                f"fail={summary['counts']['fail']} blocked={summary['counts']['blocked']}"
            )
