from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access, _limit_queryset_to_user_farms
from smart_agri.core.models.warehouse import BinLocation, InventoryStock, Warehouse, WarehouseZone
from smart_agri.core.utils import get_current_farm


class WarehouseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Warehouse.objects.all()

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


class WarehouseZoneViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = WarehouseZone.objects.all()

    def get_queryset(self):
        return _limit_queryset_to_user_farms(super().get_queryset(), self.request.user, "warehouse__farm_id__in")


class BinLocationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = BinLocation.objects.all()

    def get_queryset(self):
        return _limit_queryset_to_user_farms(super().get_queryset(), self.request.user, "zone__warehouse__farm_id__in")

    @action(detail=True, methods=["get"])
    def stock_levels(self, request, pk=None):
        bin_loc = self.get_object()
        _ensure_user_has_farm_access(request.user, bin_loc.zone.warehouse.farm_id)
        stocks = InventoryStock.objects.filter(bin_location=bin_loc)
        data = []
        for stock in stocks:
            data.append(
                {
                    "item_name": stock.item.name,
                    "quantity": stock.quantity,
                    "lot_number": stock.lot_number,
                }
            )
        return Response(data)
