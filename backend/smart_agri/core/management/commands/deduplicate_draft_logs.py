"""
Management command to deduplicate orphaned empty Draft DailyLogs.

These are created when the frontend submits a DailyLog (step 1) but the
Activity creation (step 2) fails. Each retry left behind an empty Draft.

Usage:
    python manage.py deduplicate_draft_logs
    python manage.py deduplicate_draft_logs --dry-run
    python manage.py deduplicate_draft_logs --farm-id=31
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from smart_agri.core.models.log import DailyLog


class Command(BaseCommand):
    help = "Deduplicate orphaned empty Draft DailyLog records (no activities, no employees)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting.',
        )
        parser.add_argument(
            '--farm-id',
            type=int,
            help='Limit deduplication to a specific farm ID.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        farm_id = options.get('farm_id')

        # Find all farm+date combinations that have multiple Draft logs
        qs = (
            DailyLog.objects
            .filter(status=DailyLog.STATUS_DRAFT, deleted_at__isnull=True)
            .values('farm_id', 'log_date')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )
        if farm_id:
            qs = qs.filter(farm_id=farm_id)

        total_deleted = 0
        for group in qs:
            f_id = group['farm_id']
            l_date = group['log_date']

            # Get all Draft logs for this farm+date, ordered by id (oldest first)
            logs = list(
                DailyLog.objects
                .filter(
                    farm_id=f_id,
                    log_date=l_date,
                    status=DailyLog.STATUS_DRAFT,
                    deleted_at__isnull=True,
                )
                .order_by('id')
            )

            # Keep the oldest one that has activities (or simply the oldest if none have activities)
            keeper = None
            for log in logs:
                if log.activities.filter(deleted_at__isnull=True).exists():
                    keeper = log
                    break
            if keeper is None:
                keeper = logs[0]  # Keep oldest empty log

            to_delete = [log for log in logs if log.id != keeper.id]

            if not to_delete:
                continue

            self.stdout.write(
                f"Farm {f_id}, Date {l_date}: keeping log #{keeper.id}, "
                f"deleting {len(to_delete)} orphaned logs: {[l.id for l in to_delete]}"
            )

            if not dry_run:
                for log in to_delete:
                    # Safety check: only delete if truly empty
                    has_activities = log.activities.filter(deleted_at__isnull=True).exists()
                    if has_activities:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Skipping log #{log.id} — has activities, manual review required."
                            )
                        )
                        continue
                    log.delete()
                    total_deleted += 1
                    self.stdout.write(self.style.SUCCESS(f"  Deleted log #{log.id}"))

        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY RUN] No records were deleted."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. Deleted {total_deleted} orphaned Draft logs."))
