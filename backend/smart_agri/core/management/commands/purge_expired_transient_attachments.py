from django.core.management.base import BaseCommand

from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


class Command(BaseCommand):
    help = "Purge expired transient attachment binaries while preserving metadata row state."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        qs = AttachmentPolicyService.due_for_purge_queryset()
        if options.get('dry_run'):
            self.stdout.write(self.style.WARNING(f"[dry-run] attachments_due_for_purge={qs.count()}"))
            return
        count = 0
        for attachment in qs.iterator():
            AttachmentPolicyService.purge_transient(attachment=attachment)
            attachment.save(update_fields=["name", "content_type", "deleted_at", "updated_at"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"attachments_purged={count}"))
