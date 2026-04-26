from smart_agri.integration_hub.event_contracts import FarmCreated
from smart_agri.integration_hub.outbox import build_outbox_message
from smart_agri.integration_hub.registry import get_dispatcher, integration_hub_snapshot, reset_registry


def setup_function():
    reset_registry()


def teardown_function():
    reset_registry()


def test_registry_snapshot_tracks_pending_messages(monkeypatch):
    monkeypatch.setenv('INTEGRATION_HUB_PUBLISHER', 'memory')
    reset_registry()
    dispatcher = get_dispatcher()
    dispatcher.enqueue(build_outbox_message(FarmCreated(aggregate_id='1', farm_name='North Farm'), 'farm.created'))
    snapshot = integration_hub_snapshot()
    assert snapshot['queued_messages'] == 1
    assert snapshot['pending_messages'] == 1
    assert snapshot['publisher']['name'] == 'memory'
