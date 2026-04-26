from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from smart_agri.core.models import Attachment, IntegrationOutboxEvent
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService
from smart_agri.integration_hub.persistence import persistent_outbox_snapshot


class OpsHealthService:
    """Read-only operational health snapshots for runtime and release surfaces."""

    EVIDENCE_STALE_AFTER_HOURS = 24

    @classmethod
    def _repo_root(cls) -> Path:
        return Path(settings.BASE_DIR).parent

    @classmethod
    def _load_summary_payload(cls, relative_path: str) -> tuple[dict, Path]:
        path = cls._repo_root().joinpath(relative_path)
        if not path.exists():
            return ({
                "path": relative_path,
                "status": "missing",
                "generated_at": None,
                "warning": "missing_summary",
                "payload": {},
            }, path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            return ({
                "path": relative_path,
                "status": "error",
                "generated_at": None,
                "warning": f"summary_read_failed:{exc}",
                "payload": {},
            }, path)
        return ({
            "path": relative_path,
            "status": payload.get("overall_status") or payload.get("status") or "unknown",
            "generated_at": payload.get("generated_at"),
            "axis_overall_status": payload.get("axis_overall_status"),
            "payload": payload,
        }, path)

    @classmethod
    def _summary_payload(cls, relative_path: str) -> dict:
        payload, _ = cls._load_summary_payload(relative_path)
        return {
            "path": payload.get("path"),
            "status": payload.get("status"),
            "generated_at": payload.get("generated_at"),
            "axis_overall_status": payload.get("axis_overall_status"),
        }

    @classmethod
    def _stale_warning(cls, generated_at: str | None) -> bool:
        if not generated_at:
            return True
        try:
            generated = timezone.datetime.fromisoformat(str(generated_at))
        except ValueError:
            return True
        if timezone.is_naive(generated):
            generated = timezone.make_aware(generated, timezone.get_current_timezone())
        return generated < timezone.now() - timedelta(hours=cls.EVIDENCE_STALE_AFTER_HOURS)

    @classmethod
    def release_health_snapshot(cls) -> dict:
        summaries = {
            "verify_release_gate_v21": cls._summary_payload("docs/evidence/closure/latest/verify_release_gate_v21/summary.json"),
            "verify_axis_complete_v21": cls._summary_payload("docs/evidence/closure/latest/verify_axis_complete_v21/summary.json"),
            "khameesiya_uat": cls._summary_payload("docs/evidence/uat/khameesiya/latest/summary.json"),
        }
        warnings = []
        stale_count = 0
        all_pass = True
        for key, payload in summaries.items():
            status = payload.get("status")
            if status != "PASS":
                all_pass = False
                warnings.append(f"{key}:{status}")
            if cls._stale_warning(payload.get("generated_at")):
                stale_count += 1
                warnings.append(f"{key}:stale_or_missing")
        severity = "healthy"
        if stale_count:
            severity = "attention"
        if not all_pass:
            severity = "critical"
        return {
            "generated_at": timezone.now().isoformat(),
            "authority_note": "Derived from canonical latest summaries; canonical score authority remains docs/evidence/closure/latest/*.",
            "severity": severity,
            "all_pass": all_pass,
            "stale_warning_count": stale_count,
            "warnings": warnings,
            "summaries": summaries,
        }

    @classmethod
    def release_health_detail_snapshot(cls) -> dict:
        definitions = {
            "verify_release_gate_v21": "docs/evidence/closure/latest/verify_release_gate_v21/summary.json",
            "verify_axis_complete_v21": "docs/evidence/closure/latest/verify_axis_complete_v21/summary.json",
            "khameesiya_uat": "docs/evidence/uat/khameesiya/latest/summary.json",
        }
        aggregate = cls.release_health_snapshot()
        rows = []
        for key, relative_path in definitions.items():
            loaded, path = cls._load_summary_payload(relative_path)
            raw_payload = loaded.get("payload") or {}
            generated_at = loaded.get("generated_at")
            stale = cls._stale_warning(generated_at)
            warnings = list(raw_payload.get("warnings") or [])
            if loaded.get("warning"):
                warnings.append(loaded["warning"])
            step_level = raw_payload.get("steps") or raw_payload.get("checks") or []
            step_failures = [
                step
                for step in step_level
                if str(step.get("status") or step.get("overall_status") or "").upper() not in {"", "PASS", "OK"}
            ]
            rows.append({
                "key": key,
                "path": relative_path,
                "absolute_path": str(path),
                "status": loaded.get("status"),
                "generated_at": generated_at,
                "stale": stale,
                "warnings": warnings,
                "step_failures": step_failures,
                "payload": raw_payload,
            })
        return {
            **aggregate,
            "detail_rows": rows,
        }

    @classmethod
    def integration_outbox_health_snapshot(cls) -> dict:
        snapshot = persistent_outbox_snapshot()
        dead_letter_count = int(snapshot.get("dead_letter_count", 0) or 0)
        stale_pending_count = int(snapshot.get("stale_pending_count", 0) or 0)
        locked_count = int(snapshot.get("locked_count", 0) or 0)
        retry_ready_count = int(snapshot.get("retry_ready_count", 0) or 0)
        severity = "healthy"
        if any([dead_letter_count, stale_pending_count]):
            severity = "critical" if dead_letter_count else "attention"
        elif any([locked_count, retry_ready_count]):
            severity = "attention"
        return {
            "generated_at": timezone.now().isoformat(),
            "severity": severity,
            "total": snapshot.get("total", 0),
            "counts": snapshot.get("counts", {}),
            "oldest_pending_at": snapshot.get("oldest_pending_at"),
            "dead_letter_count": dead_letter_count,
            "dead_letter_severity": "critical" if dead_letter_count else "healthy",
            "stale_pending_count": stale_pending_count,
            "stale_pending_severity": "attention" if stale_pending_count else "healthy",
            "retry_ready_count": retry_ready_count,
            "retry_backlog_buckets": {
                "retry_ready": retry_ready_count,
                "locked": locked_count,
                "dead_letter": dead_letter_count,
            },
            "worker_lock_contention_posture": "attention" if locked_count else "healthy",
            "recent_dead_letters": snapshot.get("recent_dead_letters", []),
        }

    @staticmethod
    def _outbox_reason(*, event: IntegrationOutboxEvent, now):
        if event.status == IntegrationOutboxEvent.Status.DEAD_LETTER:
            return "dead_letter"
        if event.locked_at:
            return "worker_lock_contention"
        if event.status in {IntegrationOutboxEvent.Status.PENDING, IntegrationOutboxEvent.Status.FAILED} and event.available_at and event.available_at < now - timedelta(minutes=15):
            return "stale_pending"
        if event.status == IntegrationOutboxEvent.Status.FAILED:
            return "retryable_failure"
        return "retry_ready"

    @classmethod
    def integration_outbox_detail_snapshot(
        cls,
        *,
        status_filter: str | None = None,
        event_type: str | None = None,
        farm_id: int | None = None,
        metadata_flag: str | None = None,
        limit: int = 50,
    ) -> dict:
        now = timezone.now()
        queryset = IntegrationOutboxEvent.objects.all().select_related("farm").order_by("available_at", "id")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        if metadata_flag:
            queryset = queryset.filter(**{f"metadata__{metadata_flag}": True})

        rows = []
        for event in queryset[: max(1, int(limit or 50))]:
            reason = cls._outbox_reason(event=event, now=now)
            rows.append({
                "id": event.id,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "destination": event.destination,
                "farm_id": event.farm_id,
                "farm_name": getattr(event.farm, "name", "") if event.farm_id else "",
                "status": event.status,
                "attempts": event.attempts,
                "max_attempts": event.max_attempts,
                "available_at": event.available_at.isoformat() if event.available_at else None,
                "dispatched_at": event.dispatched_at.isoformat() if event.dispatched_at else None,
                "updated_at": event.updated_at.isoformat() if event.updated_at else None,
                "last_error": event.last_error,
                "correlation_id": (event.metadata or {}).get("correlation_id") or event.event_id,
                "metadata_flag_match": bool(metadata_flag and (event.metadata or {}).get(metadata_flag)),
                "locked_at": event.locked_at.isoformat() if event.locked_at else None,
                "locked_by": event.locked_by,
                "canonical_reason": reason,
                "retry_eligible": event.status != IntegrationOutboxEvent.Status.DISPATCHED,
            })
        return {
            **cls.integration_outbox_health_snapshot(),
            "filters": {
                "status": status_filter or "",
                "event_type": event_type or "",
                "farm_id": farm_id,
                "metadata_flag": metadata_flag or "",
                "limit": max(1, int(limit or 50)),
            },
            "detail_rows": rows,
            "filtered_total": queryset.count(),
        }

    @classmethod
    def attachment_runtime_health_snapshot(cls) -> dict:
        runtime = AttachmentPolicyService.security_runtime_summary()
        pending_scan = int(runtime.get("pending_scan", 0) or 0)
        quarantined = int(runtime.get("quarantined", 0) or 0)
        due_archive = int(runtime.get("due_archive", 0) or 0)
        due_purge = int(runtime.get("due_purge", 0) or 0)
        authoritative_flags = []
        if pending_scan:
            authoritative_flags.append("pending_scan_backlog")
        if quarantined:
            authoritative_flags.append("quarantined_evidence_present")
        if due_archive:
            authoritative_flags.append("archive_transition_due")
        severity = "healthy"
        if quarantined:
            severity = "critical"
        elif pending_scan or due_archive:
            severity = "attention"
        return {
            "generated_at": timezone.now().isoformat(),
            "severity": severity,
            **runtime,
            "pending_scan_severity": "attention" if pending_scan else "healthy",
            "quarantine_severity": "critical" if quarantined else "healthy",
            "due_archive_posture": "attention" if due_archive else "healthy",
            "due_purge_posture": "attention" if due_purge else "healthy",
            "authoritative_evidence_risk_flags": authoritative_flags,
        }

    @classmethod
    def _attachment_runtime_queryset(cls, *, farm_id: int | None = None):
        queryset = Attachment.objects.filter(deleted_at__isnull=True)
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        return queryset.filter(
            Q(malware_scan_status=Attachment.MALWARE_SCAN_PENDING)
            | Q(malware_scan_status=Attachment.MALWARE_SCAN_QUARANTINED)
            | Q(
                is_authoritative_evidence=True,
                archived_at__isnull=False,
                archived_at__lte=timezone.now(),
                storage_tier=Attachment.STORAGE_TIER_HOT,
                malware_scan_status=Attachment.MALWARE_SCAN_PASSED,
            )
        ).select_related("farm").order_by("updated_at", "id")

    @classmethod
    def _attachment_risk_reason(cls, *, attachment: Attachment) -> str:
        if attachment.malware_scan_status == Attachment.MALWARE_SCAN_QUARANTINED:
            return "attachment_scan_blocked"
        if attachment.malware_scan_status == Attachment.MALWARE_SCAN_PENDING:
            return "pending_scan"
        if (
            attachment.is_authoritative_evidence
            and attachment.archived_at
            and attachment.archived_at <= timezone.now()
            and attachment.storage_tier == Attachment.STORAGE_TIER_HOT
        ):
            return "archive_transition_due"
        return "runtime_attention"

    @classmethod
    def attachment_runtime_detail_snapshot(
        cls,
        *,
        farm_id: int | None = None,
        risk_reason: str | None = None,
        limit: int = 50,
    ) -> dict:
        queryset = cls._attachment_runtime_queryset(farm_id=farm_id)
        rows = []
        for attachment in queryset[: max(1, int(limit or 50))]:
            reason = cls._attachment_risk_reason(attachment=attachment)
            if risk_reason and reason != risk_reason:
                continue
            rows.append({
                "id": attachment.id,
                "name": attachment.name or attachment.filename_original or attachment.file.name,
                "farm_id": attachment.farm_id,
                "farm_name": getattr(attachment.farm, "name", "") if attachment.farm_id else "",
                "evidence_class": attachment.evidence_class,
                "scan_state": attachment.scan_state,
                "archive_state": attachment.archive_state,
                "quarantine_state": attachment.quarantine_state,
                "authoritative_at": attachment.authoritative_at.isoformat() if attachment.authoritative_at else None,
                "archived_at": attachment.archived_at.isoformat() if attachment.archived_at else None,
                "quarantined_at": attachment.quarantined_at.isoformat() if attachment.quarantined_at else None,
                "storage_tier": attachment.storage_tier,
                "quarantine_reason": attachment.quarantine_reason,
                "canonical_reason": reason,
                "rescan_eligible": bool(
                    attachment.malware_scan_status in {Attachment.MALWARE_SCAN_PENDING, Attachment.MALWARE_SCAN_QUARANTINED}
                    and not attachment.is_authoritative_evidence
                ),
            })
        return {
            **cls.attachment_runtime_health_snapshot(),
            "filters": {
                "farm_id": farm_id,
                "risk_reason": risk_reason or "",
                "limit": max(1, int(limit or 50)),
            },
            "detail_rows": rows,
            "filtered_total": len(rows) if risk_reason else queryset.count(),
        }
