from django.core.management.base import BaseCommand

from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


class Command(BaseCommand):
    help = "Archive authoritative attachments whose archive date has matured."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        qs = AttachmentPolicyService.due_for_archive_queryset()
        if options.get('dry_run'):
            self.stdout.write(self.style.WARNING(f"[dry-run] attachments_due_for_archive={qs.count()}"))
            return
        count = 0
        for attachment in qs.iterator():
            AttachmentPolicyService.move_to_archive(attachment=attachment)
            attachment.save(update_fields=["storage_tier", "archive_backend", "archive_key", "archived_at", "updated_at"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"attachments_archived={count}"))
