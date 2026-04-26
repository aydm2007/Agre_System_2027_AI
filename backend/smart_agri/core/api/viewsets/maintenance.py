from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access, _limit_queryset_to_user_farms
from smart_agri.core.models.preventive_maintenance import MaintenanceSchedule, MaintenanceTask
from smart_agri.core.services.maintenance_service import MaintenanceService
from smart_agri.core.utils import get_current_farm


class MaintenanceScheduleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = MaintenanceSchedule.objects.all()

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


class MaintenanceTaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = MaintenanceTask.objects.all()

    def get_queryset(self):
        return _limit_queryset_to_user_farms(super().get_queryset(), self.request.user, "schedule__farm_id__in")

    @action(detail=False, methods=["post"])
    def generate_tasks(self, request):
        farm = get_current_farm(request)
        _ensure_user_has_farm_access(request.user, getattr(farm, "id", getattr(farm, "pk", None)))
        service = MaintenanceService(farm)
        tasks = service.generate_due_tasks()
        return Response({"count": len(tasks)})

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        farm = get_current_farm(request)
        _ensure_user_has_farm_access(request.user, getattr(farm, "id", getattr(farm, "pk", None)))
        service = MaintenanceService(farm)
        data = service.get_dashboard_summary()
        return Response(data)
