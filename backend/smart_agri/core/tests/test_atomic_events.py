from django.test import TestCase, TransactionTestCase
from django.db import transaction
from unittest.mock import MagicMock
from smart_agri.core.events import EventBus, DomainEvent

class TestEvent(DomainEvent):
    pass

class AtomicEventTests(TransactionTestCase):
    """
    Formal Verification for Agri-Guardian Rule: 
    'Events must be Atomic (No Ghost Events).'
    We use TransactionTestCase because standard TestCase wraps everything in a transaction 
    that never technically 'commits' in the way on_commit expects during a test run 
    unless captured properly, but on_commit hooks do run in standard TestCase 
    when the test wrapper tears down? No, standard TestCase is atomic=True.
    
    Actually, to test `on_commit`, we often need `TransactionTestCase` which tears down 
    tables or `captureOnCommitCallbacks` (Django 3.2+).
    """

    def tearDown(self):
        EventBus.reset()
        super().tearDown()

    def test_event_publishes_only_on_commit(self):
        """
        Verify that a handler wrapped in transaction.on_commit does NOT run if the transaction fails.
        """
        handler = MagicMock()
        EventBus.subscribe(TestEvent, handler)

        try:
            with transaction.atomic():
                event = TestEvent()
                EventBus.publish(event)
                # Should not have run yet (inside transaction)
                handler.assert_not_called()
                
                # Force failure
                from django.db import DatabaseError
                raise DatabaseError("Simulated DB Crash")
        except DatabaseError:
            pass

        # Should STILL not have run because transaction rolled back
        handler.assert_not_called()

    def test_event_publishes_after_commit(self):
        """
        Verify that a handler runs after a successful commit.
        """
        handler = MagicMock()
        EventBus.subscribe(TestEvent, handler)

        with transaction.atomic():
            event = TestEvent()
            EventBus.publish(event)
            # Not yet
            handler.assert_not_called()
        
        # Now it should have run (transaction block exited successfully)
        # Note: In TransactionTestCase, we might need to manually trigger on_commit execution 
        # depending on Django version/test runner, but usually it fires on block exit.
        handler.assert_called_once()
