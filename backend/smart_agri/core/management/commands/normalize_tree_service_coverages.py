from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from smart_agri.core.models import TreeServiceCoverage


class Command(BaseCommand):
    help = "Normalise TreeServiceCoverage records (scope/type alignment, counts, duplicates)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without persisting changes; prints the planned summary only.",
        )

    def handle(self, *args, **options):
        dry_run: bool = bool(options.get("dry_run"))
        stats = self._normalise_coverages(dry_run=dry_run)

        prefix = "[DRY-RUN] " if dry_run else ""
        for label, value in stats.items():
            self.stdout.write(f"{prefix}{label}: {value}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run complete; no changes were saved."))
        else:
            self.stdout.write(self.style.SUCCESS("Normalisation complete."))

    def _normalise_coverages(self, *, dry_run: bool) -> Dict[str, int]:
        stats: Dict[str, int] = defaultdict(int)

        now = timezone.now()

        with transaction.atomic():
            coverages = TreeServiceCoverage.objects.select_for_update()

            for coverage in coverages:
                if coverage.deleted_at is not None:
                    continue

                changed_fields: List[str] = []
                desired_scope = coverage.service_scope or coverage.service_type or TreeServiceCoverage.GENERAL
                desired_type = coverage.service_type or desired_scope or TreeServiceCoverage.GENERAL

                if coverage.service_scope != desired_scope:
                    coverage.service_scope = desired_scope
                    changed_fields.append("target_scope")
                if coverage.service_type != desired_type:
                    coverage.service_type = desired_type
                    changed_fields.append("service_type")

                if coverage.service_count is None or coverage.service_count < 0:
                    coverage.service_count = max(coverage.service_count or 0, 0)
                    changed_fields.append("service_count")

                if changed_fields:
                    stats["coverages_normalised"] += 1
                    if not dry_run:
                        coverage.updated_at = now
                        coverage.save(update_fields=[*changed_fields, "updated_at"])

            duplicate_groups = (
                TreeServiceCoverage.objects.filter(deleted_at__isnull=True)
                .values("activity_id", "crop_variety_id", "target_scope")
                .annotate(total=Count("id"))
                .filter(total__gt=1)
            )

            for group in duplicate_groups:
                stats["duplicate_groups"] += 1
                coverages_qs = (
                    TreeServiceCoverage.objects.filter(
                        activity_id=group["activity_id"],
                        crop_variety_id=group["crop_variety_id"],
                        target_scope=group["target_scope"],
                        deleted_at__isnull=True,
                    )
                    .select_for_update()
                    .order_by("-updated_at", "-id")
                )

                coverages_list = list(coverages_qs)
                if len(coverages_list) < 2:
                    continue

                keeper = coverages_list[0]
                extras = coverages_list[1:]

                stats["duplicate_rows"] += len(extras)

                total_count = sum((item.service_count or 0) for item in coverages_list)
                combined_notes = keeper.notes or ""
                for item in extras:
                    if item.notes and item.notes not in combined_notes:
                        combined_notes = f"{combined_notes}\n{item.notes}".strip()

                if not dry_run:
                    updates: List[str] = []
                    if keeper.service_count != total_count:
                        keeper.service_count = total_count
                        updates.append("service_count")
                    if combined_notes and keeper.notes != combined_notes:
                        keeper.notes = combined_notes
                        updates.append("notes")
                    if updates:
                        keeper.updated_at = now
                        keeper.save(update_fields=[*updates, "updated_at"])

                    for item in extras:
                        item.delete()

        return dict(stats)
