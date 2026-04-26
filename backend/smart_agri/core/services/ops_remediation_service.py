from __future__ import annotations

import logging
from io import StringIO
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from smart_agri.core.api.permissions import user_has_any_farm_role, user_has_sector_finance_authority
from smart_agri.core.models import Attachment, AuditLog, IntegrationOutboxEvent
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService


logger = logging.getLogger(__name__)


class OpsRemediationService:
    """Governed safe remediation actions for sector/system operators."""

    OPERATOR_ROLES = {
        "رئيس حسابات القطاع",
        "المدير المالي لقطاع المزارع",
        "مدير القطاع",
        "مدير النظام",
    }

    @classmethod
    def _ensure_operator(cls, *, user) -> None:
        if getattr(user, "is_superuser", False):
            return
        if user_has_sector_finance_authority(user):
            return
        if user_has_any_farm_role(user, cls.OPERATOR_ROLES):
            return
        raise PermissionDenied("Safe remediation actions are restricted to sector/system operators.")

    @staticmethod
    def _action_id() -> str:
        return f"ops-{uuid4()}"

    @staticmethod
    def _normalize_ids(ids, *, field_name: str) -> list[int]:
        if not isinstance(ids, (list, tuple)):
            raise ValidationError({field_name: "Explicit IDs list is required."})
        normalized = []
        for raw in ids:
            try:
                normalized.append(int(raw))
            except (TypeError, ValueError):
                raise ValidationError({field_name: f"Invalid ID value: {raw}"})
        normalized = sorted(set(normalized))
        if not normalized:
            raise ValidationError({field_name: "Explicit IDs list is required."})
        return normalized

    @classmethod
    def _audit(cls, *, user, action: str, model: str, object_id: str, payload: dict, reason: str = "") -> None:
        AuditLog.objects.create(
            actor=user,
            action=action,
            model=model,
            object_id=object_id[:500],
            new_payload=payload,
            reason=reason[:500],
        )

    @classmethod
    def _log_requested(cls, *, user, action_name: str, action_id: str, request_id: str | None, correlation_id: str | None, target_ids: list[int]) -> None:
        logger.info(
            "ops.remediation.requested",
            extra={
                "action_name": action_name,
                "action_id": action_id,
                "request_id": request_id,
                "correlation_id": correlation_id or action_id,
                "actor_id": getattr(user, "id", None),
                "target_ids": target_ids,
            },
        )

    @classmethod
    def _log_completed(
        cls,
        *,
        user,
        action_name: str,
        action_id: str,
        request_id: str | None,
        correlation_id: str | None,
        processed: int,
        skipped: int,
        failed: int,
    ) -> None:
        logger.info(
            "ops.remediation.completed",
            extra={
                "action_name": action_name,
                "action_id": action_id,
                "request_id": request_id,
                "correlation_id": correlation_id or action_id,
                "actor_id": getattr(user, "id", None),
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
            },
        )

    @classmethod
    def _log_failed(cls, *, user, action_name: str, action_id: str, request_id: str | None, correlation_id: str | None, error: str) -> None:
        logger.warning(
            "ops.remediation.failed",
            extra={
                "action_name": action_name,
                "action_id": action_id,
                "request_id": request_id,
                "correlation_id": correlation_id or action_id,
                "actor_id": getattr(user, "id", None),
                "error": error,
            },
        )

    @classmethod
    def retry_outbox_events(
        cls,
        *,
        user,
        event_ids,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        cls._ensure_operator(user=user)
        ids = cls._normalize_ids(event_ids, field_name="event_ids")
        action_id = cls._action_id()
        cls._log_requested(
            user=user,
            action_name="retry_outbox_events",
            action_id=action_id,
            request_id=request_id,
            correlation_id=correlation_id,
            target_ids=ids,
        )
        now = timezone.now()
        processed_rows = []
        skipped_rows = []
        failed_rows = []
        try:
            events = {row.id: row for row in IntegrationOutboxEvent.objects.filter(id__in=ids)}
            for event_id in ids:
                event = events.get(event_id)
                if event is None:
                    failed_rows.append({"id": event_id, "reason": "missing_event"})
                    continue
                if event.status == IntegrationOutboxEvent.Status.DISPATCHED:
                    skipped_rows.append({"id": event.id, "reason": "non_retryable_status", "status": event.status})
                    continue
                previous_status = event.status
                event.status = IntegrationOutboxEvent.Status.FAILED if previous_status == IntegrationOutboxEvent.Status.DEAD_LETTER else IntegrationOutboxEvent.Status.PENDING
                event.available_at = now
                event.locked_at = None
                event.locked_by = ""
                event.last_error = f"[ops-retry:{previous_status}] {event.last_error}".strip()
                event.save(update_fields=["status", "available_at", "locked_at", "locked_by", "last_error", "updated_at"])
                processed_rows.append({
                    "id": event.id,
                    "event_id": event.event_id,
                    "from_status": previous_status,
                    "to_status": event.status,
                    "correlation_id": (event.metadata or {}).get("correlation_id") or event.event_id,
                })
            result = {
                "action_id": action_id,
                "status": "completed" if not failed_rows else "partial",
                "processed": len(processed_rows),
                "skipped": len(skipped_rows),
                "failed": len(failed_rows),
                "results": {
                    "processed_rows": processed_rows,
                    "skipped_rows": skipped_rows,
                    "failed_rows": failed_rows,
                },
            }
            cls._audit(
                user=user,
                action="OPS_REMEDIATION_RETRY_OUTBOX",
                model="IntegrationOutboxEvent",
                object_id=",".join(str(value) for value in ids),
                payload=result,
                reason="Safe retry of selected outbox events.",
            )
            cls._log_completed(
                user=user,
                action_name="retry_outbox_events",
                action_id=action_id,
                request_id=request_id,
                correlation_id=correlation_id,
                processed=result["processed"],
                skipped=result["skipped"],
                failed=result["failed"],
            )
            return result
        except (ValidationError, PermissionDenied, DatabaseError, OSError, RuntimeError, ValueError) as exc:
            cls._log_failed(
                user=user,
                action_name="retry_outbox_events",
                action_id=action_id,
                request_id=request_id,
                correlation_id=correlation_id,
                error=str(exc),
            )
            cls._audit(
                user=user,
                action="OPS_REMEDIATION_RETRY_OUTBOX_FAILED",
                model="IntegrationOutboxEvent",
                object_id=",".join(str(value) for value in ids),
                payload={"action_id": action_id, "error": str(exc)},
                reason="Outbox retry remediation failed.",
            )
            raise

    @classmethod
    def rescan_attachments(
        cls,
        *,
        user,
        attachment_ids,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        cls._ensure_operator(user=user)
        ids = cls._normalize_ids(attachment_ids, field_name="attachment_ids")
        action_id = cls._action_id()
        cls._log_requested(
            user=user,
            action_name="rescan_attachments",
            action_id=action_id,
            request_id=request_id,
            correlation_id=correlation_id,
            target_ids=ids,
        )
        processed_rows = []
        skipped_rows = []
        failed_rows = []
        try:
            attachments = {row.id: row for row in Attachment.objects.filter(id__in=ids).select_related("farm")}
            for attachment_id in ids:
                attachment = attachments.get(attachment_id)
                if attachment is None:
                    failed_rows.append({"id": attachment_id, "reason": "missing_attachment"})
                    continue
                if attachment.is_authoritative_evidence:
                    skipped_rows.append({"id": attachment.id, "reason": "authoritative_evidence_locked"})
                    continue
                if attachment.storage_tier == Attachment.STORAGE_TIER_ARCHIVE:
                    skipped_rows.append({"id": attachment.id, "reason": "archived_attachment_locked"})
                    continue
                if attachment.malware_scan_status not in {Attachment.MALWARE_SCAN_PENDING, Attachment.MALWARE_SCAN_QUARANTINED}:
                    skipped_rows.append({"id": attachment.id, "reason": "scan_not_retryable", "status": attachment.malware_scan_status})
                    continue
                farm_settings = getattr(getattr(attachment, "farm", None), "settings", None)
                AttachmentPolicyService.scan_attachment(attachment=attachment, farm_settings=farm_settings)
                attachment.save(update_fields=[
                    "content_type",
                    "mime_type_detected",
                    "malware_scan_status",
                    "scan_state",
                    "quarantine_state",
                    "quarantine_reason",
                    "scanned_at",
                    "quarantined_at",
                    "updated_at",
                ])
                processed_rows.append({
                    "id": attachment.id,
                    "name": attachment.name or attachment.filename_original,
                    "status": attachment.malware_scan_status,
                    "quarantine_reason": attachment.quarantine_reason,
                })
            result = {
                "action_id": action_id,
                "status": "completed" if not failed_rows else "partial",
                "processed": len(processed_rows),
                "skipped": len(skipped_rows),
                "failed": len(failed_rows),
                "results": {
                    "processed_rows": processed_rows,
                    "skipped_rows": skipped_rows,
                    "failed_rows": failed_rows,
                },
            }
            cls._audit(
                user=user,
                action="OPS_REMEDIATION_RESCAN_ATTACHMENT",
                model="Attachment",
                object_id=",".join(str(value) for value in ids),
                payload=result,
                reason="Safe rescan of selected attachments.",
            )
            cls._log_completed(
                user=user,
                action_name="rescan_attachments",
                action_id=action_id,
                request_id=request_id,
                correlation_id=correlation_id,
                processed=result["processed"],
                skipped=result["skipped"],
                failed=result["failed"],
            )
            return result
        except (ValidationError, PermissionDenied, DatabaseError, OSError, RuntimeError, ValueError) as exc:
            cls._log_failed(
                user=user,
                action_name="rescan_attachments",
                action_id=action_id,
                request_id=request_id,
                correlation_id=correlation_id,
                error=str(exc),
            )
            cls._audit(
                user=user,
                action="OPS_REMEDIATION_RESCAN_ATTACHMENT_FAILED",
                model="Attachment",
                object_id=",".join(str(value) for value in ids),
                payload={"action_id": action_id, "error": str(exc)},
                reason="Attachment rescan remediation failed.",
            )
            raise

    @classmethod
    def dry_run_governance_maintenance(
        cls,
        *,
        user,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
        cls._ensure_operator(user=user)
        action_id = cls._action_id()
        cls._log_requested(
            user=user,
            action_name="dry_run_governance_maintenance",
            action_id=action_id,
            request_id=request_id,
            correlation_id=correlation_id,
            target_ids=[],
        )
        try:
            stdout = StringIO()
            call_command("run_governance_maintenance_cycle", dry_run=True, stdout=stdout)
            output_lines = [line.strip() for line in stdout.getvalue().splitlines() if line.strip()]
            result = {
                "action_id": action_id,
                "status": "completed",
                "processed": 0,
                "skipped": 0,
                "failed": 0,
                "results": {
                    "output_lines": output_lines,
                },
            }
            cls._audit(
                user=user,
                action="OPS_REMEDIATION_GOVERNANCE_DRY_RUN",
                model="GovernanceMaintenance",
                object_id=action_id,
                payload=result,
                reason="Safe governance maintenance dry run.",
            )
            cls._log_completed(
                user=user,
                action_name="dry_run_governance_maintenance",
                action_id=action_id,
                request_id=request_id,
                correlation_id=correlation_id,
                processed=0,
                skipped=0,
                failed=0,
            )
            return result
        except (ValidationError, PermissionDenied, CommandError, DatabaseError, OSError, RuntimeError, ValueError) as exc:
            cls._log_failed(
                user=user,
                action_name="dry_run_governance_maintenance",
                action_id=action_id,
                request_id=request_id,
                correlation_id=correlation_id,
                error=str(exc),
            )
            cls._audit(
                user=user,
                action="OPS_REMEDIATION_GOVERNANCE_DRY_RUN_FAILED",
                model="GovernanceMaintenance",
                object_id=action_id,
                payload={"action_id": action_id, "error": str(exc)},
                reason="Governance maintenance dry run failed.",
            )
            raise
