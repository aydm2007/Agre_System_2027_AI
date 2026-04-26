from __future__ import annotations

from django.core.management.base import BaseCommand

from smart_agri.integration_hub.persistence import dispatch_persistent_outbox, persistent_outbox_snapshot
from smart_agri.integration_hub.registry import get_dispatcher, integration_hub_snapshot


class Command(BaseCommand):
    help = 'Dispatch in-memory and persistent integration hub outbox messages and print an operational snapshot.'

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=100)
        parser.add_argument('--worker-name', default='manage.py dispatch_outbox')
        parser.add_argument('--metadata-flag', help='Limit dispatch to rows where metadata.<flag> is true.')

    def handle(self, *args, **options):
        dispatcher = get_dispatcher()
        processed_memory = dispatcher.dispatch_pending()
        persistent = dispatch_persistent_outbox(
            batch_size=options['batch_size'],
            worker_name=options['worker_name'],
            metadata_flag=options.get('metadata_flag'),
        )
        snapshot = integration_hub_snapshot()
        persistent_snapshot = persistent_outbox_snapshot(metadata_flag=options.get('metadata_flag'))
        self.stdout.write(self.style.SUCCESS(f'Processed {len(processed_memory)} in-memory outbox message(s).'))
        self.stdout.write(self.style.SUCCESS(
            f"Processed {persistent.processed} persistent event(s): dispatched={persistent.dispatched}, failed={persistent.failed}, dead_lettered={persistent.dead_lettered}."
        ))
        self.stdout.write(str({'memory': snapshot, 'persistent': persistent_snapshot}))
