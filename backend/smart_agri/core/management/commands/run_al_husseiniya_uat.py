from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run the official Al Husseiniya dual-mode UAT cycle and write evidence artifacts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--artifact-root",
            type=str,
            default="docs/evidence/uat/al-husseiniya",
            help="Directory where UAT evidence artifacts are written.",
        )
        parser.add_argument(
            "--clean-seed",
            action="store_true",
            default=False,
            help="Wipe and re-seed the Al Husseiniya UAT farm before running phases.",
        )

    def handle(self, *args, **options):
        from smart_agri.core.uat.al_husseiniya import run_al_husseiniya_uat

        artifact_root = Path(options["artifact_root"])
        clean_seed = options["clean_seed"]
        self.stdout.write(
            f"Starting Al Husseiniya UAT cycle (artifact_root={artifact_root}, clean_seed={clean_seed})"
        )

        report = run_al_husseiniya_uat(artifact_root=artifact_root, clean_seed=clean_seed)
        overall = report.get("overall_status", "UNKNOWN")
        summary = report.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        total = summary.get("total", 0)

        self.stdout.write(
            f"UAT complete: {passed}/{total} phases passed, {failed} failed, overall_status={overall}"
        )
        self.stdout.write(f"evidence_dir={artifact_root.resolve()}")

        if overall != "PASS":
            for failure in report.get("phases", []):
                if failure.get("status") == "FAIL":
                    self.stderr.write(self.style.ERROR(f"  FAIL: {failure['name']} — {failure['error']}"))
            raise CommandError(
                f"run_al_husseiniya_uat: {failed}/{total} phases failed. "
                f"See {artifact_root / 'summary.json'} for details."
            )

        self.stdout.write(self.style.SUCCESS("All Al Husseiniya UAT phases PASS."))
