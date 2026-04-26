"""
[AGRI-GUARDIAN] Mode Switch Quarantine Service

When switching from SIMPLE → STRICT mode, all pending/unreviewed
DailyLogs created during SIMPLE mode are quarantined for 24-hour
manager review before entering the strict financial pipeline.
"""
import logging
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.settings import SystemSettings
from smart_agri.core.models.sync_conflict import OfflineSyncQuarantine

logger = logging.getLogger(__name__)


class ModeSwitchQuarantineService:
    """
    Enforces a 24-hour quarantine window when switching
    from SIMPLE mode to STRICT mode.
    """

    QUARANTINE_WINDOW_HOURS = 24

    @staticmethod
    @transaction.atomic
    def quarantine_pending_logs_on_mode_switch(*, farm, switched_by) -> int:
        """
        Called when strict_erp_mode is toggled from False → True.

        Finds all DailyLogs in DRAFT/SUBMITTED status created during
        SIMPLE mode and quarantines them for manager review.

        Returns: number of quarantined entries.
        """
        cutoff = timezone.now() - timedelta(hours=ModeSwitchQuarantineService.QUARANTINE_WINDOW_HOURS)

        # Find logs that were created in SIMPLE mode and are not yet approved
        pending_logs = DailyLog.objects.filter(
            farm=farm,
            status__in=[DailyLog.STATUS_DRAFT, DailyLog.STATUS_SUBMITTED],
            created_at__gte=cutoff,
            deleted_at__isnull=True,
        ).select_for_update()

        quarantined_count = 0
        for log in pending_logs:
            idemp_key = f"mode-switch-quarantine-log-{log.id}"

            # Skip if already quarantined
            if OfflineSyncQuarantine.objects.filter(
                idempotency_key=idemp_key,
                deleted_at__isnull=True,
            ).exists():
                continue

            OfflineSyncQuarantine.objects.create(
                farm=farm,
                submitted_by=log.created_by,
                variance_type='MODE_SWITCH_QUARANTINE',
                device_timestamp=log.created_at,
                server_intercept_time=timezone.now(),
                original_payload={
                    'daily_log_id': log.id,
                    'log_date': str(log.log_date),
                    'status_before': log.status,
                    'reason': 'Auto-quarantined during Simple→Strict mode switch',
                },
                idempotency_key=idemp_key,
                status='PENDING_REVIEW',
            )

            # Mark log as requiring review (keep it in current state but tag it)
            if not log.variance_note:
                log.variance_note = ''
            log.variance_note += ' [⚠️ تم حجر هذا السجل بسبب التبديل إلى الوضع الصارم]'
            log.save(update_fields=['variance_note', 'updated_at'])

            quarantined_count += 1

        if quarantined_count > 0:
            logger.info(
                "ModeSwitchQuarantine: Quarantined %d pending logs for farm=%s by user=%s",
                quarantined_count, farm.id, switched_by.id,
            )

        return quarantined_count

    @staticmethod
    def get_quarantine_stats(farm) -> dict:
        """Get quarantine queue counts for a farm."""
        qs = OfflineSyncQuarantine.objects.filter(
            farm=farm,
            deleted_at__isnull=True,
        )
        return {
            'pending': qs.filter(status='PENDING_REVIEW').count(),
            'approved': qs.filter(status='APPROVED_AND_POSTED').count(),
            'rejected': qs.filter(status='REJECTED').count(),
        }

    @staticmethod
    @transaction.atomic
    def resolve_quarantine(*, quarantine_id: int, action: str, manager, reason: str = '') -> 'OfflineSyncQuarantine':
        """
        Resolve a quarantined entry.
        action: 'approve' or 'reject'
        """
        entry = OfflineSyncQuarantine.objects.select_for_update().get(
            pk=quarantine_id,
            status='PENDING_REVIEW',
            deleted_at__isnull=True,
        )

        if action == 'approve':
            entry.status = 'APPROVED_AND_POSTED'
            entry.manager_signature = manager
            entry.resolved_at = timezone.now()
            entry.resolution_reason = reason or 'Approved by manager after quarantine review'
            entry.save()

            # Restore the log to its pre-quarantine state
            log_id = entry.original_payload.get('daily_log_id')
            if log_id:
                try:
                    log = DailyLog.objects.get(pk=log_id)
                    # Clean up quarantine note
                    if log.variance_note:
                        log.variance_note = log.variance_note.replace(
                            ' [⚠️ تم حجر هذا السجل بسبب التبديل إلى الوضع الصارم]', ''
                        )
                        log.save(update_fields=['variance_note', 'updated_at'])
                except DailyLog.DoesNotExist:
                    pass

            logger.info(
                "Quarantine #%s APPROVED by manager=%s",
                quarantine_id, manager.id,
            )

        elif action == 'reject':
            entry.status = 'REJECTED'
            entry.manager_signature = manager
            entry.resolved_at = timezone.now()
            entry.resolution_reason = reason or 'Rejected by manager during quarantine review'
            entry.save()

            logger.info(
                "Quarantine #%s REJECTED by manager=%s",
                quarantine_id, manager.id,
            )

        return entry
