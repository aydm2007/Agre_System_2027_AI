import os

from django.test import TestCase

from smart_agri.integration_hub.event_contracts import FarmCreated, InventoryChanged
from smart_agri.integration_hub.persistence import dispatch_persistent_outbox, persist_event, persistent_outbox_snapshot
from smart_agri.integration_hub.registry import get_publisher, reset_registry
from smart_agri.integration_hub.outbox import OutboxDispatcher, build_outbox_message, OutboxStatus
from smart_agri.core.models import IntegrationOutboxEvent


class DummyPublisher:
    def __init__(self):
        self.published = []

    def publish(self, destination, payload):
        self.published.append((destination, payload))


def test_event_contracts_are_serializable():
    event = FarmCreated(aggregate_id='1', farm_name='Alpha', owner_id='42', farm_id='1')
    payload = event.to_dict()
    assert payload['event_type'] == 'farm.created'
    assert payload['payload']['farm_name'] == 'Alpha'


def test_outbox_dispatcher_marks_messages_dispatched():
    publisher = DummyPublisher()
    dispatcher = OutboxDispatcher(publisher=publisher)
    message = build_outbox_message(InventoryChanged(aggregate_id='sku-1', sku='SKU1', delta_quantity=5), 'market-sync')
    dispatcher.enqueue(message)
    dispatcher.dispatch_pending()
    assert message.status == OutboxStatus.DISPATCHED
    assert publisher.published[0][0] == 'market-sync'


class ReadinessPublisherContractTests(TestCase):
    def setUp(self):
        self.original_mode = os.environ.get('INTEGRATION_HUB_PUBLISHER')
        os.environ['INTEGRATION_HUB_PUBLISHER'] = 'readiness_composite'
        reset_registry()

    def tearDown(self):
        if self.original_mode is None:
            os.environ.pop('INTEGRATION_HUB_PUBLISHER', None)
        else:
            os.environ['INTEGRATION_HUB_PUBLISHER'] = self.original_mode
        reset_registry()

    def test_registry_returns_readiness_composite_publisher(self):
        publisher = get_publisher()
        self.assertEqual(publisher.name, 'readiness_composite')
        described = publisher.describe()
        self.assertEqual(described['name'], 'readiness_composite')
        self.assertEqual([entry['name'] for entry in described['publishers']], ['logging', 'readiness_evidence'])

    def test_dispatch_persistent_outbox_supports_success_retry_and_dead_letter(self):
        success = persist_event(
            InventoryChanged(aggregate_id='sku-ok', sku='OK', delta_quantity=1, event_id='readiness-success-1'),
            destination='readiness/success',
        )
        retryable = persist_event(
            InventoryChanged(aggregate_id='sku-retry', sku='RETRY', delta_quantity=1, event_id='readiness-retry-1'),
            destination='readiness/retry',
        )
        dead_letter = persist_event(
            InventoryChanged(aggregate_id='sku-dead', sku='DEAD', delta_quantity=1, event_id='readiness-dead-1'),
            destination='readiness/dead-letter',
        )
        dead_letter.attempts = dead_letter.max_attempts - 1
        dead_letter.save(update_fields=['attempts', 'updated_at'])

        result = dispatch_persistent_outbox(batch_size=10, worker_name='test-readiness')
        self.assertEqual(result.processed, 3)
        self.assertEqual(result.dispatched, 1)
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.dead_lettered, 1)

        success.refresh_from_db()
        retryable.refresh_from_db()
        dead_letter.refresh_from_db()

        self.assertEqual(success.status, IntegrationOutboxEvent.Status.DISPATCHED)
        self.assertEqual(retryable.status, IntegrationOutboxEvent.Status.FAILED)
        self.assertEqual(retryable.last_error, 'readiness_retryable_failure')
        self.assertEqual(dead_letter.status, IntegrationOutboxEvent.Status.DEAD_LETTER)
        self.assertEqual(dead_letter.last_error, 'readiness_dead_letter_failure')

        snapshot = persistent_outbox_snapshot()
        self.assertGreaterEqual(snapshot['counts'].get('dispatched', 0), 1)
        self.assertGreaterEqual(snapshot['counts'].get('failed', 0), 1)
        self.assertGreaterEqual(snapshot['dead_letter_count'], 1)
