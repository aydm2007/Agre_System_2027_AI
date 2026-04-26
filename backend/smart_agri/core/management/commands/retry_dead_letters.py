from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from smart_agri.core.models import IntegrationOutboxEvent


class Command(BaseCommand):
    help = 'Move dead-lettered outbox events back to failed or pending so workers can retry them.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--to-status', choices=['pending', 'failed'], default='failed')
        parser.add_argument('--metadata-flag', help='Limit retries to rows where metadata.<flag> is true.')

    def handle(self, *args, **options):
        query = IntegrationOutboxEvent.objects.filter(status=IntegrationOutboxEvent.Status.DEAD_LETTER)
        metadata_flag = options.get('metadata_flag')
        if metadata_flag:
            query = query.filter(**{f'metadata__{metadata_flag}': True})
        items = list(query.order_by('updated_at', 'id')[:options['limit']])
        count = 0
        for item in items:
            item.status = options['to_status']
            item.available_at = timezone.now()
            item.locked_at = None
            item.locked_by = ''
            item.last_error = f"[manual-retry] {item.last_error}".strip()
            item.save(update_fields=['status', 'available_at', 'locked_at', 'locked_by', 'last_error', 'updated_at'])
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Requeued {count} dead-letter event(s).'))
