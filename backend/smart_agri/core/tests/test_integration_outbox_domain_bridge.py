from django.test import TestCase

from smart_agri.integration_hub.event_contracts import ActivityLogged
from smart_agri.integration_hub.persistence import persist_event
from smart_agri.core.models import IntegrationOutboxEvent


class IntegrationOutboxBridgeTests(TestCase):
    def test_persist_event_creates_pending_row(self):
        event = ActivityLogged(aggregate_id='123', activity_type='irrigation', quantity=2, farm_id='7')
        row = persist_event(event, destination='activity-events')
        self.assertEqual(row.status, IntegrationOutboxEvent.Status.PENDING)
        self.assertEqual(row.destination, 'activity-events')
        self.assertEqual(row.event_type, 'activity.logged')
