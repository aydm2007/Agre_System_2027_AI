from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access, _limit_queryset_to_user_farms
from smart_agri.core.api.serializers import (
    CustodyIssueSerializer,
    CustodyTransferSerializer,
    CustodyTransitionSerializer,
)
from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.core.models import CustodyTransfer, Farm, Location, Supervisor
from smart_agri.core.services.custody_transfer_service import CustodyTransferService
from smart_agri.inventory.models import Item


class CustodyTransferViewSet(AuditedModelViewSet):
    queryset = CustodyTransfer.objects.filter(deleted_at__isnull=True).select_related(
        "farm",
        "supervisor",
        "item",
        "source_location",
        "custody_location",
    )
    serializer_class = CustodyTransferSerializer
    permission_classes = [permissions.IsAuthenticated]
    model_name = "CustodyTransfer"
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = _limit_queryset_to_user_farms(super().get_queryset(), self.request.user, "farm_id__in")
        farm_id = self.request.query_params.get("farm_id") or self.request.query_params.get("farm")
        supervisor_id = self.request.query_params.get("supervisor_id") or self.request.query_params.get("supervisor")
        status_value = self.request.query_params.get("status")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        if supervisor_id:
            qs = qs.filter(supervisor_id=supervisor_id)
        if status_value:
            qs = qs.filter(status=status_value)
        return qs

    @action(detail=False, methods=["post"], url_path="issue")
    def issue(self, request):
        serializer = CustodyIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        farm_id = serializer.validated_data["farm_id"]
        _ensure_user_has_farm_access(request.user, farm_id)
        key, error_response = self._enforce_action_idempotency(request, farm_id=farm_id)
        if error_response:
            return error_response

        farm = Farm.objects.get(pk=farm_id)
        supervisor = Supervisor.objects.get(pk=serializer.validated_data["supervisor_id"], farm=farm)
        item = Item.objects.get(pk=serializer.validated_data["item_id"])
        source_location = Location.objects.get(pk=serializer.validated_data["from_location_id"], farm=farm)
        transfer = CustodyTransferService.issue_transfer(
            farm=farm,
            supervisor=supervisor,
            item=item,
            source_location=source_location,
            qty=serializer.validated_data["qty"],
            actor=request.user,
            batch_number=serializer.validated_data.get("batch_number") or "",
            note=serializer.validated_data.get("note") or "",
            allow_top_up=serializer.validated_data.get("allow_top_up", False),
            idempotency_key=key or "",
        )
        response = Response(self.get_serializer(transfer).data, status=status.HTTP_201_CREATED)
        self._commit_action_idempotency(request, key, object_id=str(transfer.id), response=response)
        return response

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        transfer = self.get_object()
        _ensure_user_has_farm_access(request.user, transfer.farm_id)
        key, error_response = self._enforce_action_idempotency(request, farm_id=transfer.farm_id)
        if error_response:
            return error_response
        serializer = CustodyTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transfer = CustodyTransferService.accept_transfer(
            transfer=transfer,
            actor=request.user,
            note=serializer.validated_data.get("note") or "",
        )
        response = Response(self.get_serializer(transfer).data)
        self._commit_action_idempotency(request, key, object_id=str(transfer.id), response=response)
        return response

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        transfer = self.get_object()
        _ensure_user_has_farm_access(request.user, transfer.farm_id)
        key, error_response = self._enforce_action_idempotency(request, farm_id=transfer.farm_id)
        if error_response:
            return error_response
        serializer = CustodyTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transfer = CustodyTransferService.reject_transfer(
            transfer=transfer,
            actor=request.user,
            note=serializer.validated_data.get("note") or "",
        )
        response = Response(self.get_serializer(transfer).data)
        self._commit_action_idempotency(request, key, object_id=str(transfer.id), response=response)
        return response

    @action(detail=True, methods=["post"], url_path="return")
    def return_transfer(self, request, pk=None):
        transfer = self.get_object()
        _ensure_user_has_farm_access(request.user, transfer.farm_id)
        key, error_response = self._enforce_action_idempotency(request, farm_id=transfer.farm_id)
        if error_response:
            return error_response
        serializer = CustodyTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transfer = CustodyTransferService.return_transfer(
            transfer=transfer,
            actor=request.user,
            qty=serializer.validated_data.get("qty"),
            note=serializer.validated_data.get("note") or "",
        )
        response = Response(self.get_serializer(transfer).data)
        self._commit_action_idempotency(request, key, object_id=str(transfer.id), response=response)
        return response

    @action(detail=False, methods=["get"], url_path="balance")
    def balance(self, request):
        return _custody_balance_response(request)

    def handle_exception(self, exc):
        if isinstance(exc, DjangoValidationError):
            detail = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        return super().handle_exception(exc)


def _custody_balance_response(request):
    farm_id = request.query_params.get("farm_id") or request.query_params.get("farm")
    supervisor_id = request.query_params.get("supervisor_id") or request.query_params.get("supervisor")
    if not farm_id or not supervisor_id:
        raise ValidationError({"detail": "farm_id و supervisor_id مطلوبان."})
    _ensure_user_has_farm_access(request.user, farm_id)
    farm = Farm.objects.get(pk=farm_id)
    supervisor = Supervisor.objects.get(pk=supervisor_id, farm=farm)
    return Response(CustodyTransferService.custody_balance_payload(farm=farm, supervisor=supervisor))


class CustodyBalanceViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def list(self, request):
        return _custody_balance_response(request)

    def handle_exception(self, exc):
        if isinstance(exc, DjangoValidationError):
            detail = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        return super().handle_exception(exc)
