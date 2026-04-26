from django.contrib import admin
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from smart_agri.core.throttles import AuthRateThrottle


# [AGRI-GUARDIAN] Custom auth views with dedicated throttle.
# The global AnonRateThrottle (100/day) is too restrictive for login endpoints
# and causes 429 lockout when other anonymous traffic exists.
class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [AuthRateThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthRateThrottle]


# --- التعديل الأول: استدعاء الدالة الجديدة ---
# --- التعديل الأول: استدعاء الدالة الجديدة ---
from smart_agri.core.api import (
    router as core_router,
    advanced_report,
    dashboard_stats,
    request_advanced_report_job,
    advanced_report_job_status,
    export_templates,
    export_jobs,
    create_export_job,
    export_job_status,
    export_job_download,
    import_templates,
    import_jobs,
    import_template_download,
    upload_import_job,
    validate_import_job,
    import_job_preview,
    apply_import_job,
    import_job_error_download,
)
from smart_agri.core.api.traceability import batch_timeline
from smart_agri.core.api.views_suggestions import SuggestionView

from smart_agri.accounts.api import router as accounts_router
from smart_agri.integrations.api import router as integrations_router
from smart_agri.sales.api import router as sales_router
from smart_agri.finance.api import router as finance_router
from smart_agri.core.api.hr import router as hr_router, worker_kpi, attendance_calendar, advances_list, approve_advance
from smart_agri.core import views_ui as ui
from smart_agri.core.api.burn_rate_api import burn_rate_summary
from smart_agri.core.api.shadow_cost_summary_api import shadow_cost_summary
from smart_agri.core.api.viewsets.audit import log_ui_breach
from smart_agri.core.observability import livez, readyz, metrics_summary, platform_metrics_summary, prometheus_metrics
from smart_agri.integration_hub.api import integration_hub_status, integration_hub_diagnostics, integration_hub_outbox_status

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """A simple endpoint to check if the service is running."""
    return Response({"status": "ok", "version": "2.0"})


# --- API URL Patterns ---
api_patterns = [
    path("health/", health, name="health"),
    path("health/live/", livez, name="livez"),
    path("health/ready/", readyz, name="readyz"),
    path("health/metrics-summary/", metrics_summary, name="metrics_summary"),
    path("health/integration-hub/", integration_hub_status, name="integration_hub_status"),
    path("health/integration-hub/diagnostics/", integration_hub_diagnostics, name="integration_hub_diagnostics"),
    path("health/integration-hub/outbox/", integration_hub_outbox_status, name="integration_hub_outbox_status"),
    path("health/platform-metrics/", platform_metrics_summary, name="platform_metrics_summary"),
    path("health/prometheus/", prometheus_metrics, name="prometheus_metrics"),
    path("auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Application Routers (v1)
    path("v1/", include(core_router.urls)),
    path("v1/", include(accounts_router.urls)),
    path("v1/", include(integrations_router.urls)),
    path("v1/", include(sales_router.urls)),
    path("v1/finance/", include("smart_agri.finance.urls")),
    path("v1/", include(hr_router.urls)),

    # Function-based bootstrap endpoints
    path("v1/seed-tree-inventory/", __import__("smart_agri.core.api.viewsets.seed_tree_inventory", fromlist=["seed_tree_inventory"]).seed_tree_inventory),

    # --- التعديل الثاني: إضافة الرابط للدالة الذكية ---
    path("v1/advanced-report/requests/", request_advanced_report_job, name="advanced_report_requests"),
    path("v1/advanced-report/requests/<int:request_id>/", advanced_report_job_status, name="advanced_report_request_status"),
    path("v1/advanced-report/", advanced_report, name="advanced_report"),
    path("v1/export-templates/", export_templates, name="export_templates"),
    path("v1/export-jobs/", export_jobs, name="export_jobs"),
    path("v1/export-jobs/create/", create_export_job, name="export_jobs_create"),
    path("v1/export-jobs/<int:job_id>/", export_job_status, name="export_job_status"),
    path("v1/export-jobs/<int:job_id>/download/", export_job_download, name="export_job_download"),
    path("v1/import-templates/", import_templates, name="import_templates"),
    path("v1/import-jobs/", import_jobs, name="import_jobs"),
    path("v1/import-templates/<str:template_code>/download/", import_template_download, name="import_template_download"),
    path("v1/import-jobs/upload/", upload_import_job, name="import_job_upload"),
    path("v1/import-jobs/<int:job_id>/validate/", validate_import_job, name="import_job_validate"),
    path("v1/import-jobs/<int:job_id>/preview/", import_job_preview, name="import_job_preview"),
    path("v1/import-jobs/<int:job_id>/apply/", apply_import_job, name="import_job_apply"),
    path("v1/import-jobs/<int:job_id>/errors/download/", import_job_error_download, name="import_job_error_download"),
    path("v1/dashboard-stats/", dashboard_stats, name="dashboard_stats"),
    path("v1/traceability/batch/<str:batch_number>/", batch_timeline, name="batch_timeline"),
    # [Phase 10] Smart Context (The Oracle)
    path("v1/suggestions/", SuggestionView.as_view(), name="suggestions"),
    path("v1/worker-kpi/", worker_kpi, name="worker_kpi"),
    path("v1/attendance-calendar/", attendance_calendar, name="attendance_calendar"),
    path("v1/advances/", advances_list, name="advances_list"),
    path("v1/advances/<int:advance_id>/approve/", approve_advance, name="approve_advance"),
    # [AGRI-GUARDIAN Axis 8+15] Burn Rate Micro-Dashboard API
    path("v1/burn-rate-summary/", burn_rate_summary, name="burn_rate_summary"),
    # [AGRI-GUARDIAN V21 §7.2] Shadow Cost Summary — SIMPLE mode shadow accounting surface
    path("v1/shadow-cost-summary/", shadow_cost_summary, name="shadow_cost_summary"),
    path("v1/audit/breach/", log_ui_breach, name="audit_ui_breach"),

    # [AGRI-GUARDIAN] Real-time notifications via SSE
    path("v1/notifications/stream/",
         __import__("smart_agri.core.api.notifications_sse", fromlist=["notifications_stream"]).notifications_stream,
         name="notifications_stream"),
]

# --- Server-Side UI (HTMX) URL Patterns ---
ui_patterns = [
    path("farms/", ui.farms_list, name="ui_farms"),
    path("logs/new", ui.daily_log_new, name="ui_daily_log_new"),
    path("audit/", ui.audit_list, name="ui_audit"),
    path("crop-tasks/", ui.crop_tasks, name="ui_crop_tasks"),
    path("partials/crops/<int:farm_id>/", ui.options_crops_for_farm, name="opts_crops"),
    path("partials/tasks/<int:crop_id>/", ui.options_tasks_for_crop, name="opts_tasks"),
    path("partials/locations/<int:farm_id>/", ui.options_locations_for_farm, name="opts_locs"),
    path("partials/assets/<int:farm_id>/", ui.options_assets_for_farm, name="opts_assets"),
]


# --- Main URL Configuration ---
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api_patterns)),
    path("ui/", include(ui_patterns)),
]

# Serve media files in development / staging
from django.conf import settings
from django.urls import re_path
from django.views.static import serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT, 'show_indexes': settings.DEBUG}),
]
