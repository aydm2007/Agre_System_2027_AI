from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
import logging

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from smart_agri.core.models import IntegrationOutboxEvent
from .event_contracts import IntegrationEvent
from .registry import get_publisher

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DispatchResult:
    processed: int = 0
    dispatched: int = 0
    failed: int = 0
    dead_lettered: int = 0


def persist_event(
    event: IntegrationEvent,
    destination: str = 'events',
    *,
    farm_id: int | None = None,
    activity_id: int | None = None,
    created_by_id: int | None = None,
) -> IntegrationOutboxEvent:
    return IntegrationOutboxEvent.objects.create(
        event_id=event.event_id,
        event_type=event.event_type,
        aggregate_type=event.aggregate_type,
        aggregate_id=str(event.aggregate_id),
        destination=destination,
        farm_id=farm_id,
        activity_id=activity_id,
        created_by_id=created_by_id,
        payload=event.payload,
        metadata={**event.metadata, 'version': event.version, 'correlation_id': event.metadata.get('correlation_id') or event.event_id},
        occurred_at=timezone.datetime.fromisoformat(event.occurred_at.replace('Z', '+00:00')) if event.occurred_at else None,
    )


def publish_event_after_commit(
    event: IntegrationEvent,
    destination: str = 'events',
    **kwargs: Any,
) -> None:
    transaction.on_commit(lambda: persist_event(event, destination=destination, **kwargs))


def _backoff_seconds(attempts: int) -> int:
    return min(300, max(5, attempts * attempts * 5))


def _apply_metadata_flag_filter(queryset, metadata_flag: str | None):
    if not metadata_flag:
        return queryset
    return queryset.filter(**{f"metadata__{metadata_flag}": True})


def dispatch_persistent_outbox(
    *,
    batch_size: int = 100,
    worker_name: str = 'manual-dispatch',
    metadata_flag: str | None = None,
) -> DispatchResult:
    publisher = get_publisher()
    result = DispatchResult()
    now = timezone.now()
    candidates_qs = _apply_metadata_flag_filter(
        IntegrationOutboxEvent.objects.filter(
            status__in=[IntegrationOutboxEvent.Status.PENDING, IntegrationOutboxEvent.Status.FAILED],
            available_at__lte=now,
        ),
        metadata_flag,
    )
    candidates = list(candidates_qs.order_by('available_at', 'id')[:batch_size])
    for item in candidates:
        result.processed += 1
        locked = IntegrationOutboxEvent.objects.filter(
            pk=item.pk,
            locked_at__isnull=True,
        ).update(locked_at=timezone.now(), locked_by=worker_name)
        if not locked:
            continue
        item.refresh_from_db()
        try:
            publisher.publish(item.destination, {
                'event_id': item.event_id,
                'event_type': item.event_type,
                'aggregate_type': item.aggregate_type,
                'aggregate_id': item.aggregate_id,
                'payload': item.payload,
                'metadata': item.metadata,
                'occurred_at': item.occurred_at.isoformat() if item.occurred_at else None,
                'farm_id': item.farm_id,
            })
            item.status = IntegrationOutboxEvent.Status.DISPATCHED
            item.dispatched_at = timezone.now()
            item.last_error = ''
            result.dispatched += 1
            logger.info(
                'outbox.dispatch.succeeded',
                extra={
                    'correlation_id': item.metadata.get('correlation_id') or item.event_id,
                    'event_id': item.event_id,
                    'event_type': item.event_type,
                    'destination': item.destination,
                    'farm_id': item.farm_id,
                    'status': item.status,
                },
            )
        except (TimeoutError, ConnectionError, OSError, ValueError, RuntimeError) as exc:  # pragma: no cover
            item.attempts += 1
            item.last_error = str(exc)
            item.available_at = timezone.now() + timedelta(seconds=_backoff_seconds(item.attempts))
            if item.attempts >= item.max_attempts:
                item.status = IntegrationOutboxEvent.Status.DEAD_LETTER
                result.dead_lettered += 1
                logger.warning(
                    'outbox.dispatch.failed',
                    extra={
                        'correlation_id': item.metadata.get('correlation_id') or item.event_id,
                        'event_id': item.event_id,
                        'event_type': item.event_type,
                        'destination': item.destination,
                        'farm_id': item.farm_id,
                        'attempts': item.attempts,
                        'status': item.status,
                        'last_error': item.last_error,
                    },
                )
            else:
                item.status = IntegrationOutboxEvent.Status.FAILED
                result.failed += 1
                logger.warning(
                    'outbox.dispatch.failed',
                    extra={
                        'correlation_id': item.metadata.get('correlation_id') or item.event_id,
                        'event_id': item.event_id,
                        'event_type': item.event_type,
                        'destination': item.destination,
                        'farm_id': item.farm_id,
                        'attempts': item.attempts,
                        'status': item.status,
                        'last_error': item.last_error,
                    },
                )
        finally:
            item.locked_at = None
            item.locked_by = ''
            item.save(update_fields=['status', 'attempts', 'last_error', 'available_at', 'dispatched_at', 'locked_at', 'locked_by', 'updated_at'])
    return result


def persistent_outbox_snapshot(*, metadata_flag: str | None = None) -> dict[str, Any]:
    now = timezone.now()
    scoped_events = _apply_metadata_flag_filter(IntegrationOutboxEvent.objects.all(), metadata_flag)
    grouped = scoped_events.values('status').annotate(total=Count('id'))
    counts = {row['status']: row['total'] for row in grouped}
    pending_qs = scoped_events.filter(status__in=[IntegrationOutboxEvent.Status.PENDING, IntegrationOutboxEvent.Status.FAILED])
    oldest_pending = pending_qs.order_by('available_at').values_list('available_at', flat=True).first()
    locked_count = scoped_events.filter(locked_at__isnull=False).count()
    retry_ready_count = pending_qs.filter(available_at__lte=now).count()
    stale_pending_count = pending_qs.filter(available_at__lt=now - timedelta(minutes=15)).count()
    recent_dead_letters = list(
        scoped_events
        .filter(status=IntegrationOutboxEvent.Status.DEAD_LETTER)
        .order_by('-updated_at')
        .values('event_id', 'event_type', 'attempts', 'last_error', 'updated_at')[:10]
    )
    return {
        'total': scoped_events.count(),
        'counts': counts,
        'oldest_pending_at': oldest_pending.isoformat() if oldest_pending else None,
        'dead_letter_count': counts.get(IntegrationOutboxEvent.Status.DEAD_LETTER, 0),
        'locked_count': locked_count,
        'retry_ready_count': retry_ready_count,
        'stale_pending_count': stale_pending_count,
        'recent_dead_letters': [
            {
                **row,
                'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
            }
            for row in recent_dead_letters
        ],
    }
