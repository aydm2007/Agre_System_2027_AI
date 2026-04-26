from __future__ import annotations

import logging

from celery import shared_task

from smart_agri.integration_hub.persistence import dispatch_persistent_outbox

logger = logging.getLogger(__name__)


@shared_task
def dispatch_integration_outbox_async(batch_size: int = 100):
    result = dispatch_persistent_outbox(batch_size=batch_size, worker_name='celery-outbox-worker')
    logger.info(
        '[Async] Integration outbox batch completed: processed=%s dispatched=%s failed=%s dead_lettered=%s',
        result.processed,
        result.dispatched,
        result.failed,
        result.dead_lettered,
    )
    return {
        'processed': result.processed,
        'dispatched': result.dispatched,
        'failed': result.failed,
        'dead_lettered': result.dead_lettered,
    }
