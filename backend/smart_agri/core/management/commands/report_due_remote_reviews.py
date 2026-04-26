from django.core.management.base import BaseCommand

from smart_agri.core.services.remote_review_service import RemoteReviewService


class Command(BaseCommand):
    help = "Report SMALL/remote farms whose weekly sector remote review is overdue."

    def handle(self, *args, **options):
        due = RemoteReviewService.report_due_reviews()
        snapshot = RemoteReviewService.governance_snapshot()
        for row in due:
            self.stdout.write(
                f"farm_id={row['farm_id']} name={row['farm_name']} last_review_at={row['last_review_at']} overdue={row['is_overdue']} escalations={','.join(row.get('open_escalation_levels') or [])}"
            )
        self.stdout.write(self.style.SUCCESS(
            f"remote_reviews_due={snapshot['due_count']} overdue={snapshot['overdue_count']} open_escalations={snapshot['open_escalations']} blocked={snapshot['blocked_escalations']}"
        ))
