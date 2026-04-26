from unittest.mock import MagicMock

from django.db import transaction
from django.test import TransactionTestCase

from smart_agri.core.events import AgriEventBus


class NamedEventBusTests(TransactionTestCase):
    def tearDown(self):
        AgriEventBus.reset()
        super().tearDown()

    def test_named_event_publishes_only_after_commit(self):
        handler = MagicMock()
        AgriEventBus.subscribe('activity_committed')(handler)

        try:
            with transaction.atomic():
                AgriEventBus.publish('activity_committed', activity_id=1, user_id=2)
                handler.assert_not_called()
                raise RuntimeError('rollback')
        except RuntimeError:
            pass

        handler.assert_not_called()

    def test_named_event_can_publish_immediately_when_requested(self):
        handler = MagicMock()
        AgriEventBus.subscribe('activity_committed')(handler)

        AgriEventBus.publish('activity_committed', publish_after_commit=False, activity_id=10)

        handler.assert_called_once()
