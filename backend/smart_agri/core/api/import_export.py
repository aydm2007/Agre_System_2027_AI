from __future__ import annotations

import mimetypes
import threading
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from smart_agri.core.models import AsyncImportJob, AsyncReportRequest
from smart_agri.core.services.import_export_platform_service import ImportExportPlatformService


def _assert_export_job_access(*, request, job: AsyncReportRequest) -> None:
    if request.user.is_superuser:
        return
    if job.created_by_id != request.user.id:
        raise PermissionDenied("ليس لك صلاحية على مهمة التصدير هذه.")


def _job_payload(job: AsyncReportRequest):
    return {
        "id": job.id,
        "status": job.status,
        "export_type": job.export_type,
        "format": job.output_format,
        "template_code": job.template_code,
        "template_version": job.template_version,
        "result_url": job.result_url,
        "output_filename": job.output_filename,
        "error_message": job.error_message,
        "metadata": job.metadata,
        "requested_at": job.requested_at,
        "completed_at": job.completed_at,
    }


def _import_job_payload(job: AsyncImportJob):
    return {
        "id": job.id,
        "status": job.status,
        "module": job.module,
        "template_code": job.template_code,
        "template_version": job.template_version,
        "mode_context": job.mode_context,
        "farm_id": job.farm_id,
        "row_count": job.row_count,
        "applied_count": job.applied_count,
        "rejected_count": job.rejected_count,
        "validation_summary": job.validation_summary,
        "result_summary": job.result_summary,
        "error_message": job.error_message,
        "preview_rows": job.preview_rows,
        "error_workbook_url": job.error_workbook.url if job.error_workbook else "",
        "metadata": job.metadata,
        "requested_at": job.requested_at,
        "validated_at": job.validated_at,
        "applied_at": job.applied_at,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_templates(request):
    return Response(
        {
            "results": ImportExportPlatformService.available_export_templates(
                actor=request.user,
                farm_id=request.query_params.get("farm_id"),
                report_group=request.query_params.get("report_group"),
                ui_surface=request.query_params.get("ui_surface"),
            )
        }
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def export_jobs(request):
    if request.method == "POST":
        job = ImportExportPlatformService.create_export_job(actor=request.user, payload=request.data or {})

        def _runner():
            ImportExportPlatformService.generate_export_job(job)

        threading.Thread(target=_runner, name=f"export-job-{job.id}", daemon=True).start()
        return Response(_job_payload(job), status=202)

    jobs = ImportExportPlatformService.list_export_jobs(
        actor=request.user,
        farm_id=request.query_params.get("farm_id"),
        limit=int(request.query_params.get("limit", 20)),
    )
    return Response({"results": [_job_payload(job) for job in jobs]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_export_job(request):
    job = ImportExportPlatformService.create_export_job(actor=request.user, payload=request.data or {})

    def _runner():
        ImportExportPlatformService.generate_export_job(job)

    threading.Thread(target=_runner, name=f"export-job-{job.id}", daemon=True).start()
    return Response(_job_payload(job), status=202)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_job_status(request, job_id: int):
    try:
        job = AsyncReportRequest.objects.get(pk=job_id)
    except AsyncReportRequest.DoesNotExist as exc:
        raise NotFound("مهمة التصدير غير موجودة.") from exc
    _assert_export_job_access(request=request, job=job)
    return Response(_job_payload(job))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_job_download(request, job_id: int):
    try:
        job = AsyncReportRequest.objects.get(pk=job_id)
    except AsyncReportRequest.DoesNotExist as exc:
        raise NotFound("مهمة التصدير غير موجودة.") from exc
    _assert_export_job_access(request=request, job=job)
    if job.status != AsyncReportRequest.STATUS_COMPLETED or not job.result_url:
        raise ValidationError("ملف التصدير غير جاهز بعد.")
    media_relative = job.result_url.replace("/media/", "", 1)
    absolute_path = Path(settings.MEDIA_ROOT) / media_relative
    if not absolute_path.exists():
        raise NotFound("ملف التصدير غير موجود.")
    content_type, _ = mimetypes.guess_type(str(absolute_path))
    return FileResponse(
        absolute_path.open("rb"),
        as_attachment=True,
        filename=job.output_filename or absolute_path.name,
        content_type=content_type or "application/octet-stream",
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_templates(request):
    return Response(
        {
            "results": ImportExportPlatformService.available_import_templates(
                actor=request.user,
                farm_id=request.query_params.get("farm_id"),
                module=request.query_params.get("module"),
            )
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_jobs(request):
    jobs = ImportExportPlatformService.list_import_jobs(
        actor=request.user,
        farm_id=request.query_params.get("farm_id"),
        limit=int(request.query_params.get("limit", 20)),
        module=request.query_params.get("module"),
    )
    return Response({"results": [_import_job_payload(job) for job in jobs]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_template_download(request, template_code: str):
    farm_id = request.query_params.get("farm_id")
    workbook_bytes = ImportExportPlatformService.build_template_workbook(
        actor=request.user,
        farm_id=farm_id,
        template_code=template_code,
        context={"crop_plan_id": request.query_params.get("crop_plan_id")},
    )
    filename = f"{template_code}-{farm_id or 'farm'}.xlsx"
    response = FileResponse(
        BytesIO(workbook_bytes),
        as_attachment=True,
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_import_job(request):
    upload = request.FILES.get("file")
    if upload is None:
        raise ValidationError({"file": "ملف Excel مطلوب."})
    template_code = request.data.get("template_code")
    farm_id = request.data.get("farm_id")
    job = ImportExportPlatformService.create_import_job(
        actor=request.user,
        farm_id=farm_id,
        template_code=template_code,
        upload=upload,
        context={"crop_plan_id": request.data.get("crop_plan_id")},
    )
    return Response(_import_job_payload(job), status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_import_job(request, job_id: int):
    try:
        job = AsyncImportJob.objects.get(pk=job_id)
    except AsyncImportJob.DoesNotExist as exc:
        raise NotFound("مهمة الاستيراد غير موجودة.") from exc
    ImportExportPlatformService.validate_import_job(actor=request.user, job=job)
    job.refresh_from_db()
    return Response(_import_job_payload(job))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_job_preview(request, job_id: int):
    try:
        job = AsyncImportJob.objects.get(pk=job_id)
    except AsyncImportJob.DoesNotExist as exc:
        raise NotFound("مهمة الاستيراد غير موجودة.") from exc
    ImportExportPlatformService._assert_job_access(actor=request.user, job=job)
    return Response(_import_job_payload(job))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def apply_import_job(request, job_id: int):
    try:
        job = AsyncImportJob.objects.get(pk=job_id)
    except AsyncImportJob.DoesNotExist as exc:
        raise NotFound("مهمة الاستيراد غير موجودة.") from exc
    ImportExportPlatformService.apply_import_job(actor=request.user, job=job)
    job.refresh_from_db()
    return Response(_import_job_payload(job))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_job_error_download(request, job_id: int):
    try:
        job = AsyncImportJob.objects.get(pk=job_id)
    except AsyncImportJob.DoesNotExist as exc:
        raise NotFound("مهمة الاستيراد غير موجودة.") from exc
    ImportExportPlatformService._assert_job_access(actor=request.user, job=job)
    if not job.error_workbook:
        raise NotFound("لا يوجد ملف أخطاء لهذه المهمة.")
    content_type, _ = mimetypes.guess_type(job.error_workbook.path)
    return FileResponse(
        job.error_workbook.open("rb"),
        as_attachment=True,
        filename=Path(job.error_workbook.name).name,
        content_type=content_type or "application/octet-stream",
    )
