from django.core.management.base import BaseCommand

from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


class Command(BaseCommand):
    help = 'Scan pending attachments, marking them passed or quarantined under the governed lifecycle.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        if options.get('dry_run'):
            pending = AttachmentPolicyService.due_for_scan_queryset().count()
            self.stdout.write(self.style.WARNING(f'[dry-run] attachments_pending_scan={pending}'))
            return

        passed = 0
        quarantined = 0
        for attachment in AttachmentPolicyService.due_for_scan_queryset().iterator():
            AttachmentPolicyService.scan_attachment(attachment=attachment, farm_settings=None)
            attachment.save(update_fields=[
                'content_type', 'malware_scan_status', 'quarantine_reason', 'scanned_at', 'quarantined_at', 'updated_at'
            ])
            if attachment.malware_scan_status == attachment.MALWARE_SCAN_QUARANTINED:
                quarantined += 1
            else:
                passed += 1
        self.stdout.write(self.style.SUCCESS(f'attachments_scanned_passed={passed} quarantined={quarantined}'))
