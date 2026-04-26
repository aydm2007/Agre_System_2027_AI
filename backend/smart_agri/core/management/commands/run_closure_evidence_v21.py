from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from smart_agri.core.services.release_verification_service import (
    build_closure_evidence_steps,
    execute_suite,
    repo_root_from_backend_dir,
)


class Command(BaseCommand):
    help = "Run the canonical V21 closure-evidence suite and write a deterministic readiness bundle."

    def add_arguments(self, parser):
        parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend lint/test/build steps.")

    def handle(self, *args, **options):
        repo_root = repo_root_from_backend_dir(Path(settings.BASE_DIR))
        summary = execute_suite(
            repo_root=repo_root,
            command_name="run_closure_evidence_v21",
            title="V21 Closure Evidence",
            steps=build_closure_evidence_steps(repo_root, skip_frontend=options["skip_frontend"]),
            artifact_paths=(
                "backend/release_readiness_snapshot.json",
                "backend/release_readiness_snapshot.md",
            ),
        )
        for step in summary["steps"]:
            self.stdout.write(f"{step['status']}: {step['label']}")
        self.stdout.write(self.style.SUCCESS(f"evidence_dir={summary['suite_dir']}"))
        self.stdout.write(f"overall_status={summary['overall_status']}")
        if summary["overall_status"] != "PASS":
            raise CommandError(
                f"run_closure_evidence_v21 incomplete: status={summary['overall_status']} "
                f"fail={summary['counts']['fail']} blocked={summary['counts']['blocked']}"
            )
