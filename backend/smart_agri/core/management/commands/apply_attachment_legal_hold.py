from django.core.management.base import BaseCommand, CommandError

from smart_agri.core.models.log import Attachment
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


class Command(BaseCommand):
    help = 'Mark an attachment as legal hold.'

    def add_arguments(self, parser):
        parser.add_argument('attachment_id', type=int)

    def handle(self, *args, **options):
        try:
            attachment = Attachment.objects.get(pk=options['attachment_id'])
        except Attachment.DoesNotExist as exc:
            raise CommandError('Attachment not found.') from exc
        AttachmentPolicyService.apply_legal_hold(attachment=attachment)
        attachment.save(update_fields=['evidence_class', 'expires_at', 'updated_at'])
        self.stdout.write(self.style.SUCCESS(f'attachment_legal_hold_applied={attachment.pk}'))
