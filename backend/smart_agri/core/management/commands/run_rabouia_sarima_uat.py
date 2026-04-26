"""
Management command wrapper for the Rabouia–Sarima dual-farm UAT cycle.

Invoked by Playwright E2E specs (e.g. fixed-assets.spec.js) and by the
backend test suite via ``call_command("run_rabouia_sarima_uat", ...)``.

[AGRI-GUARDIAN / AGENTS.md] This command seeds two canonical farms
(الربوعية SIMPLE, الصارمة STRICT) and runs the full UAT phase battery
defined in ``smart_agri.core.uat.rabouia_sarima``.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Run the Rabouia–Sarima dual-farm UAT cycle and write evidence "
        "artifacts (summary.json, summary.md, phases log)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--artifact-root",
            type=str,
            default="docs/evidence/uat/rabouia-sarima",
            help="Directory where UAT evidence artifacts are written.",
        )
        parser.add_argument(
            "--clean-seed",
            action="store_true",
            default=False,
            help="Wipe and re-seed UAT farm data before running phases.",
        )

    def handle(self, *args, **options):
        from smart_agri.core.uat.rabouia_sarima import run_rabouia_sarima_uat

        artifact_root = Path(options["artifact_root"])
        clean_seed = options["clean_seed"]

        self.stdout.write(
            f"Starting Rabouia–Sarima UAT cycle "
            f"(artifact_root={artifact_root}, clean_seed={clean_seed})"
        )

        report = run_rabouia_sarima_uat(
            artifact_root=artifact_root,
            clean_seed=clean_seed,
        )

        overall = report.get("overall_status", "UNKNOWN")
        summary = report.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        total = summary.get("total", 0)

        self.stdout.write(
            f"UAT complete: {passed}/{total} phases passed, "
            f"{failed} failed, overall_status={overall}"
        )
        self.stdout.write(f"evidence_dir={artifact_root.resolve()}")

        if overall != "PASS":
            failures = report.get("failures", [])
            for f in failures:
                self.stderr.write(
                    self.style.ERROR(
                        f"  FAIL: {f['name']} — {f['diagnostic']}"
                    )
                )
            raise CommandError(
                f"run_rabouia_sarima_uat: {failed}/{total} phases failed. "
                f"See {artifact_root / 'summary.json'} for details."
            )

        self.stdout.write(self.style.SUCCESS("All UAT phases PASS."))
