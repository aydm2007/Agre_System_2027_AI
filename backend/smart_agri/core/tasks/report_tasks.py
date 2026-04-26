from celery import shared_task
from django.conf import settings
from django.urls import reverse
from pathlib import Path
import json
import logging
from django.core.serializers.json import DjangoJSONEncoder
from django.db import OperationalError
from rest_framework.exceptions import ValidationError

from rest_framework.test import APIRequestFactory
from rest_framework.test import force_authenticate
from django.contrib.auth.models import AnonymousUser

from smart_agri.core.models.report import AsyncReportRequest
from smart_agri.core.services.reporting_service import ArabicReportService
from smart_agri.core.services.activity_service import ActivityService
from smart_agri.core.api.reporting import advanced_report

logger = logging.getLogger(__name__)


def _generate_pdf_report(report_request_id: int):
    try:
        report_request = AsyncReportRequest.objects.get(pk=report_request_id)
    except AsyncReportRequest.DoesNotExist:
        logger.error("AsyncReportRequest %s not found", report_request_id)
        return

    report_request.mark_running()
    try:
        service = ArabicReportService()
        params = report_request.params or {}
        
        if report_request.report_type == AsyncReportRequest.REPORT_COMMERCIAL_PDF:
            pdf_bytes = service.generate_commercial_pdf(params)
            filename = f"commercial_report_{report_request.id}.pdf"
        else:
            pdf_bytes = service.generate_profitability_pdf(params)
            filename = f"profitability_report_{report_request.id}.pdf"
        
        # Save to Media Root
        media_root = Path(settings.MEDIA_ROOT)
        reports_dir = media_root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        file_path = reports_dir / filename
        
        with file_path.open("wb") as fh:
            fh.write(pdf_bytes)
            
        pdf_url = f"/media/reports/{filename}"
        report_request.mark_completed(pdf_url)
        logger.info("Async profitability report ready: %s", pdf_url)
    except (ValidationError, OperationalError, RuntimeError, ValueError, TypeError) as exc:
        report_request.mark_failed(str(exc))
        logger.exception("Profitability report failed: %s", exc)


@shared_task(bind=True)
def generate_profitability_report(self, report_request_id: int):
    _generate_pdf_report(report_request_id)


@shared_task(bind=True)
def generate_commercial_report(self, report_request_id: int):
    _generate_pdf_report(report_request_id)


@shared_task(bind=True)
def generate_advanced_report(self, report_request_id: int):
    try:
        report_request = AsyncReportRequest.objects.select_related('created_by').get(pk=report_request_id)
    except AsyncReportRequest.DoesNotExist:
        logger.error("Advanced AsyncReportRequest %s not found", report_request_id)
        return

    report_request.mark_running()
    try:
        params = report_request.params or {}
        factory = APIRequestFactory()
        request = factory.get("/api/v1/advanced-report/", data=params)
        force_authenticate(request, user=report_request.created_by or AnonymousUser())
        response = advanced_report(request)
        if response.status_code != 200:
            raise ValueError(f"Advanced report request failed with status {response.status_code}")

        payload = response.data
        media_root = Path(settings.MEDIA_ROOT)
        reports_dir = media_root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        filename = f"advanced-report-{report_request.id}.json"
        file_path = reports_dir / filename
        with file_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder)

        result_url = f"/media/reports/{filename}"
        report_request.mark_completed(result_url)
        logger.info("Advanced report ready: %s", result_url)
    except (ValidationError, OperationalError, RuntimeError, ValueError, TypeError) as exc:
        report_request.mark_failed(str(exc))
        logger.exception("Advanced report task failed: %s", exc)
