from django.core.management.base import BaseCommand

from smart_agri.core.services.remote_review_service import RemoteReviewService


class Command(BaseCommand):
    help = 'Report overdue remote-review farms that should be blocked from selected STRICT finance actions.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = bool(options.get('dry_run'))
        if dry_run:
            rows = [row for row in RemoteReviewService.report_due_reviews() if row.get('is_overdue')]
        else:
            rows = RemoteReviewService.overdue_farms()
        snapshot = RemoteReviewService.governance_snapshot()
        for row in rows:
            self.stdout.write(
                f"farm_id={row['farm_id']} name={row['farm_name']} overdue_since={row['last_review_at']} escalation_id={row.get('escalation_id')}"
            )
        message = f"remote_reviews_overdue={len(rows)} blocked_escalations={snapshot['blocked_escalations']}"
        if dry_run:
            self.stdout.write(self.style.WARNING(f"[dry-run] {message}"))
            return
        self.stdout.write(self.style.SUCCESS(message))
