from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from smart_agri.core.services.release_verification_service import (
    build_static_steps,
    execute_suite,
    repo_root_from_backend_dir,
)


class Command(BaseCommand):
    help = "Run the canonical V21 static verification suite and write evidence artifacts."

    def handle(self, *args, **options):
        repo_root = repo_root_from_backend_dir(Path(settings.BASE_DIR))
        summary = execute_suite(
            repo_root=repo_root,
            command_name="verify_static_v21",
            title="V21 Static Verification",
            steps=build_static_steps(repo_root),
            artifact_paths=("backend/scripts/release_gate_float_check.txt",),
        )
        for step in summary["steps"]:
            self.stdout.write(f"{step['status']}: {step['label']}")
        self.stdout.write(self.style.SUCCESS(f"evidence_dir={summary['suite_dir']}"))
        self.stdout.write(f"overall_status={summary['overall_status']}")
        if summary["overall_status"] != "PASS":
            raise CommandError(
                f"verify_static_v21 incomplete: status={summary['overall_status']} "
                f"fail={summary['counts']['fail']} blocked={summary['counts']['blocked']}"
            )
