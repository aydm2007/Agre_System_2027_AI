from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access, _limit_queryset_to_user_farms
from smart_agri.core.models.dynamic_report import ReportTemplate, SavedReport
from smart_agri.core.services.report_builder import ReportBuilderService
from smart_agri.core.utils import get_current_farm


class ReportTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ReportTemplate.objects.all()

    def get_queryset(self):
        return _limit_queryset_to_user_farms(super().get_queryset(), self.request.user, "farm_id__in")

    def perform_create(self, serializer):
        farm = get_current_farm(self.request)
        _ensure_user_has_farm_access(self.request.user, getattr(farm, "id", getattr(farm, "pk", None)))
        serializer.save(farm=farm)

    def perform_update(self, serializer):
        farm = serializer.validated_data.get("farm") or getattr(serializer.instance, "farm", None)
        _ensure_user_has_farm_access(self.request.user, getattr(farm, "id", getattr(farm, "pk", None)))
        serializer.save()

    def perform_destroy(self, instance):
        _ensure_user_has_farm_access(self.request.user, instance.farm_id)
        super().perform_destroy(instance)

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        template = self.get_object()
        _ensure_user_has_farm_access(request.user, template.farm_id)
        params = request.data.get("params", {})
        service = ReportBuilderService(template.farm)
        saved_report = service.execute_template(template, params)
        return Response(saved_report.result_data)


class SavedReportViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = SavedReport.objects.all()

    def get_queryset(self):
        return _limit_queryset_to_user_farms(super().get_queryset(), self.request.user, "template__farm_id__in")
