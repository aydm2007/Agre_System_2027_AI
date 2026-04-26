from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from smart_agri.core.services.qr_operation_service import QROperationService

from .base import IdempotentCreateMixin


class QROperationsViewSet(IdempotentCreateMixin, viewsets.ViewSet):
    """
    @idempotent
    [YECO Shadow ERP] QR operation endpoints.
    """

    permission_classes = [permissions.IsAuthenticated]
    enforce_idempotency = True

    @action(detail=False, methods=["post"])
    def resolve(self, request):
        farm_id = request.data.get("farm_id")
        key, error_response = self._enforce_action_idempotency(request, farm_id=farm_id)
        if error_response:
            return error_response
        try:
            payload = QROperationService.resolve(
                actor=request.user,
                qr_string=request.data.get("qr_string", ""),
                farm_id=farm_id,
            )
            response = Response(payload, status=status.HTTP_200_OK)
            self._commit_action_idempotency(request, key, response=response)
            return response
        except ValidationError as exc:
            return Response(getattr(exc, "detail", {"detail": str(exc)}), status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as exc:
            return Response(getattr(exc, "detail", {"detail": str(exc)}), status=status.HTTP_403_FORBIDDEN)

    @action(detail=False, methods=["post"])
    def execute(self, request):
        """
        @idempotent
        Requires X-Idempotency-Key and routes mutations through service layer.
        """
        farm_id = request.data.get("farm_id")
        key, error_response = self._enforce_action_idempotency(request, farm_id=farm_id)
        if error_response:
            return error_response

        try:
            payload = QROperationService.execute(
                actor=request.user,
                qr_string=request.data.get("qr_string", ""),
                action_type=request.data.get("action"),
                farm_id=farm_id,
                location_id=request.data.get("location_id"),
                amount=request.data.get("amount", "0"),
                note=request.data.get("note", ""),
                idempotency_key=request.headers.get("X-Idempotency-Key"),
            )
            response = Response(payload, status=status.HTTP_201_CREATED)
            self._commit_action_idempotency(request, key, response=response)
            return response
        except ValidationError as exc:
            return Response(getattr(exc, "detail", {"detail": str(exc)}), status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as exc:
            return Response(getattr(exc, "detail", {"detail": str(exc)}), status=status.HTTP_403_FORBIDDEN)
