from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from smart_agri.core.models import IntegrationOutboxEvent


class Command(BaseCommand):
    help = 'Purge old dispatched outbox events to control table growth.'

    def add_arguments(self, parser):
        parser.add_argument('--older-than-hours', type=int, default=168)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--metadata-flag', help='Limit purge to rows where metadata.<flag> is true.')

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=options['older_than_hours'])
        qs = IntegrationOutboxEvent.objects.filter(
            status=IntegrationOutboxEvent.Status.DISPATCHED,
            dispatched_at__lt=cutoff,
        )
        metadata_flag = options.get('metadata_flag')
        if metadata_flag:
            qs = qs.filter(**{f'metadata__{metadata_flag}': True})
        total = qs.count()
        if options['dry_run']:
            self.stdout.write(self.style.WARNING(f'[dry-run] Would purge {total} dispatched outbox event(s).'))
            return
        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f'Purged {deleted} dispatched outbox event row(s).'))
