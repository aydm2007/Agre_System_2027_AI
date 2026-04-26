from django.core.management.base import BaseCommand, CommandError

from smart_agri.core.models.log import Attachment
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


class Command(BaseCommand):
    help = 'Restore archived attachment metadata back to hot tier.'

    def add_arguments(self, parser):
        parser.add_argument('attachment_id', type=int)

    def handle(self, *args, **options):
        try:
            attachment = Attachment.objects.get(pk=options['attachment_id'])
        except Attachment.DoesNotExist as exc:
            raise CommandError('Attachment not found.') from exc
        AttachmentPolicyService.restore_from_archive(attachment=attachment)
        attachment.save(update_fields=['storage_tier', 'restored_at', 'updated_at'])
        self.stdout.write(self.style.SUCCESS(f'attachment_restored={attachment.pk}'))
