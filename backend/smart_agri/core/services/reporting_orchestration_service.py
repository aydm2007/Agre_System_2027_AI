import logging
import threading
from datetime import timedelta
from decimal import Decimal

from django.db import close_old_connections, transaction
from django.utils import timezone
from kombu.exceptions import OperationalError as KombuOperationalError
from rest_framework.exceptions import PermissionDenied, ValidationError

from smart_agri.core.models.farm import Farm
from smart_agri.core.models.report import AsyncReportRequest, VarianceAlert

logger = logging.getLogger(__name__)


class ReportingOrchestrationService:
    """Service-layer orchestration for async advanced-report workflow."""

    REPORT_STALLED_WINDOW = timedelta(seconds=12)

    @staticmethod
    def create_advanced_report_request(*, actor, params: dict) -> AsyncReportRequest:
        report_type = params.get('report_type', AsyncReportRequest.REPORT_ADVANCED)
        if report_type == 'profitability_pdf':
            report_type = AsyncReportRequest.REPORT_PROFITABILITY
        elif report_type == AsyncReportRequest.REPORT_COMMERCIAL_PDF:
            report_type = AsyncReportRequest.REPORT_COMMERCIAL_PDF

        with transaction.atomic():
            return AsyncReportRequest.objects.create(
                created_by=actor,
                report_type=report_type,
                params=params or {},
            )

    @staticmethod
    def enqueue_or_fallback(*, actor, job: AsyncReportRequest, params: dict, inline_generator) -> None:
        def _dispatch() -> None:
            close_old_connections()
            try:
                try:
                    from smart_agri.core.tasks.report_tasks import (
                        generate_advanced_report,
                        generate_commercial_report,
                        generate_profitability_report,
                    )
                except ImportError as exc:  # pragma: no cover - defensive import guard
                    logger.warning("Celery tasks unavailable, running inline advanced report: %s", exc)
                    ReportingOrchestrationService._fallback_inline(
                        actor=actor,
                        job=job,
                        params=params,
                        inline_generator=inline_generator,
                        reason=str(exc),
                    )
                    return

                try:
                    if job.report_type == AsyncReportRequest.REPORT_PROFITABILITY:
                        generate_profitability_report.delay(job.id)
                    elif job.report_type == AsyncReportRequest.REPORT_COMMERCIAL_PDF:
                        generate_commercial_report.delay(job.id)
                    else:
                        generate_advanced_report.delay(job.id)
                except (
                    AttributeError,
                    RuntimeError,
                    OSError,
                    ConnectionError,
                    TypeError,
                    ValueError,
                    KombuOperationalError,
                ) as exc:  # pragma: no cover
                    logger.exception(
                        "Failed to enqueue advanced report job %s; falling back to inline",
                        job.id,
                    )
                    ReportingOrchestrationService._fallback_inline(
                        actor=actor,
                        job=job,
                        params=params,
                        inline_generator=inline_generator,
                        reason=str(exc),
                    )
            finally:
                close_old_connections()

        thread = threading.Thread(
            target=_dispatch,
            name=f"report-dispatch-{job.id}",
            daemon=True,
        )
        thread.start()

    @staticmethod
    def _fallback_inline(*, actor, job: AsyncReportRequest, params: dict, inline_generator, reason: str = "") -> None:
        farm = ReportingOrchestrationService._resolve_farm_for_alert(actor=actor, params=params)
        if farm is not None:
            VarianceAlert.objects.create(
                farm=farm,
                category=VarianceAlert.CATEGORY_OTHER,
                activity_name="Celery Fallback: Inline Reporting",
                alert_message=(
                    f"Heavy advanced report '{job.id}' ran inline because Celery queue was unavailable. "
                    f"This may affect system performance. reason={reason}"
                ).strip(),
                variance_amount=Decimal("0.0000"),
                variance_percentage=Decimal("0.00"),
            )
        ReportingOrchestrationService._run_inline_generation_async(job=job, inline_generator=inline_generator)

    @staticmethod
    def _resolve_farm_for_alert(*, actor, params: dict):
        from smart_agri.core.api.permissions import user_farm_ids

        farm_id = params.get("farm") or params.get("farm_id")
        if farm_id and isinstance(farm_id, str) and "," in farm_id:
            farm_id = farm_id.split(",")[0]

        if not farm_id:
            if actor.is_superuser:
                farm = Farm.objects.first()
            else:
                ids = user_farm_ids(actor)
                farm = Farm.objects.filter(id__in=ids).first() if ids else None
            if farm is not None:
                params["farm_id"] = farm.id
            return farm

        farm = Farm.objects.filter(id=farm_id).first()
        if farm is None:
            raise ValidationError({"farm_id": "Invalid farm_id. Farm not found."})
        if not actor.is_superuser and farm.id not in set(user_farm_ids(actor)):
            raise PermissionDenied("?? ???? ?????? ??? ??? ???????.")
        return farm

    @staticmethod
    def _run_inline_generation_async(*, job: AsyncReportRequest, inline_generator) -> None:
        def _runner():
            close_old_connections()
            try:
                inline_generator(job)
            finally:
                close_old_connections()

        thread = threading.Thread(
            target=_runner,
            name=f"report-inline-{job.id}",
            daemon=True,
        )
        thread.start()

    @staticmethod
    def is_stalled(job: AsyncReportRequest) -> bool:
        if job.status not in {AsyncReportRequest.STATUS_PENDING, AsyncReportRequest.STATUS_RUNNING}:
            return False
        if job.result_url:
            return False
        requested_at = job.requested_at or timezone.now()
        return requested_at <= timezone.now() - ReportingOrchestrationService.REPORT_STALLED_WINDOW

    @staticmethod
    def rescue_stalled_job(*, job: AsyncReportRequest, inline_generator):
        rescue_triggered = False
        stalled = False

        with transaction.atomic():
            locked_job = AsyncReportRequest.objects.select_for_update().get(pk=job.pk)
            stalled = ReportingOrchestrationService.is_stalled(locked_job)
            metadata = dict(locked_job.metadata or {})
            rescue_state = dict(metadata.get("rescue") or {})
            rescue_attempted = bool(rescue_state.get("attempted_at"))

            if (
                stalled
                and not rescue_attempted
                and locked_job.status in {AsyncReportRequest.STATUS_PENDING, AsyncReportRequest.STATUS_RUNNING}
                and not locked_job.result_url
            ):
                rescue_state.update(
                    {
                        "attempted_at": timezone.now().isoformat(),
                        "reason": "stalled_status_poll",
                        "state": "inline_fallback_requested",
                    }
                )
                metadata["rescue"] = rescue_state
                locked_job.metadata = metadata
                locked_job.save(update_fields=["metadata"])
                rescue_triggered = True

        if rescue_triggered:
            logger.warning("Rescuing stalled advanced report job %s via inline fallback", job.pk)
            ReportingOrchestrationService._run_inline_generation_async(
                job=job,
                inline_generator=inline_generator,
            )

        job.refresh_from_db()
        return job, ReportingOrchestrationService.is_stalled(job), rescue_triggered
