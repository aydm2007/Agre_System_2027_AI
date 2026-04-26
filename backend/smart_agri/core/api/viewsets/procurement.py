from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access, _limit_queryset_to_user_farms
from smart_agri.core.models.procurement import RequestForQuotation, SupplierQuotation
from smart_agri.core.services.procurement_service import ProcurementService
from smart_agri.core.utils import get_current_farm


class RFQViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = RequestForQuotation.objects.all()

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
    def issue(self, request, pk=None):
        rfq = self.get_object()
        _ensure_user_has_farm_access(request.user, rfq.farm_id)
        service = ProcurementService(rfq.farm)
        try:
            service.issue_rfq(rfq)
            return Response({"status": "RFQ issued"})
        except (ValidationError, DjangoValidationError, PermissionDenied) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def award(self, request, pk=None):
        rfq = self.get_object()
        quotation_id = request.data.get("quotation_id")
        if not quotation_id:
            return Response({"error": "quotation_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        _ensure_user_has_farm_access(request.user, rfq.farm_id)
        service = ProcurementService(rfq.farm)
        try:
            po = service.award_rfq(rfq, quotation_id)
            return Response(
                {
                    "status": "RFQ awarded",
                    "purchase_order_id": po.id,
                    "purchase_order_number": po.id,
                }
            )
        except (SupplierQuotation.DoesNotExist, ValidationError, DjangoValidationError, PermissionDenied) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class QuotationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = SupplierQuotation.objects.all()

    def get_queryset(self):
        return _limit_queryset_to_user_farms(super().get_queryset(), self.request.user, "rfq__farm_id__in")
