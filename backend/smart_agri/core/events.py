from collections import defaultdict
from typing import Callable, Type, List, DefaultDict
import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import OperationalError
from django.dispatch import Signal
from django.utils import timezone

logger = logging.getLogger(__name__)


class DomainEvent:
    """Base class for all domain events."""

    def __init__(self):
        self.timestamp = timezone.now()


class ActivityCreated(DomainEvent):
    def __init__(self, activity, user):
        super().__init__()
        self.activity = activity
        self.user = user


class ActivityUpdated(DomainEvent):
    def __init__(self, activity, user, changes: dict = None):
        super().__init__()
        self.activity = activity
        self.user = user
        self.changes = changes or {}


class ActivityDeleted(DomainEvent):
    def __init__(self, activity, user):
        super().__init__()
        self.activity = activity
        self.user = user


class _TransactionalDispatcher:
    """Shared commit-aware dispatch helpers for named and typed domain events."""

    @staticmethod
    def defer(callback: Callable[[], None], publish_after_commit: bool = True) -> None:
        if publish_after_commit:
            transaction.on_commit(callback)
        else:
            callback()


class AgriEventBus:
    """
    Unified named event bus for intra-process domain notifications.
    Uses Django Signals underneath and defers publication until commit by default.
    """

    EVENTS = {
        'activity_committed': Signal(),  # input: activity_id, user_id, is_new
        'tree_stock_updated': Signal(),
        'inventory_consumed': Signal(),
        'financial_transaction_posted': Signal(),
    }

    @classmethod
    def publish(
        cls,
        event_name: str,
        sender: object = None,
        publish_after_commit: bool = True,
        **kwargs,
    ) -> None:
        signal = cls.EVENTS.get(event_name)
        if signal is None:
            logger.warning("AgriEventBus received unknown event '%s' from %s", event_name, sender)
            return

        logger.debug("Publishing named event '%s'", event_name)

        def _dispatch() -> None:
            try:
                signal.send(sender=sender or cls, **kwargs)
            except (ValidationError, OperationalError, RuntimeError):
                logger.exception("Named event '%s' failed during dispatch", event_name)
                raise

        _TransactionalDispatcher.defer(_dispatch, publish_after_commit=publish_after_commit)

    @classmethod
    def subscribe(cls, event_name: str):
        def decorator(receiver_func):
            signal = cls.EVENTS.get(event_name)
            if signal is not None:
                signal.connect(receiver_func)
            return receiver_func

        return decorator

    @classmethod
    def reset(cls) -> None:
        for signal in cls.EVENTS.values():
            signal.receivers = []


class EventBus:
    """Legacy typed event bus retained for backward compatibility with existing listeners/tests."""

    _subscribers: DefaultDict[Type[DomainEvent], List[Callable]] = defaultdict(list)

    @classmethod
    def subscribe(cls, event_type: Type[DomainEvent], handler: Callable) -> None:
        if handler not in cls._subscribers[event_type]:
            cls._subscribers[event_type].append(handler)

    @classmethod
    def publish(cls, event: DomainEvent, publish_after_commit: bool = True) -> None:
        event_type = type(event)
        handlers = list(cls._subscribers.get(event_type, []))

        def _dispatch() -> None:
            for handler in handlers:
                handler(event)

        _TransactionalDispatcher.defer(_dispatch, publish_after_commit=publish_after_commit)

    @classmethod
    def reset(cls) -> None:
        cls._subscribers.clear()
