from django.core.exceptions import ValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from smart_agri.core.api.viewsets.base import IdempotentCreateMixin
from smart_agri.core.services.fuel_reconciliation_service import FuelReconciliationService


class FuelReconciliationDashboardViewSet(IdempotentCreateMixin, viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    enforce_idempotency = True

    def list(self, request):
        payload = FuelReconciliationService.build_dashboard_payload(
            user=request.user,
            farm_id=request.query_params.get("farm_id") or request.headers.get("X-Farm-ID"),
            tank=request.query_params.get("tank"),
        )
        return Response(payload)

    @action(detail=False, methods=["post"], url_path="post-reconciliation")
    def post_reconciliation(self, request):
        """
        Approve a fuel alert and post the accounting entry for the FuelLog.
        Body: {daily_log_id, fuel_log_id, reason, ref_id}
        """
        data = request.data or {}
        try:
            daily_log_id = int(data.get("daily_log_id"))
            fuel_log_id = int(data.get("fuel_log_id"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "daily_log_id and fuel_log_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = (data.get("reason") or "").strip()
        ref_id = data.get("ref_id") or ""
        if not reason:
            return Response(
                {"detail": "Settlement reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response

        try:
            from smart_agri.core.services.fuel_reconciliation_posting_service import (
                FuelReconciliationPostingService,
            )

            result = FuelReconciliationPostingService.approve_and_post(
                user=request.user,
                daily_log_id=daily_log_id,
                fuel_log_id=fuel_log_id,
                reason=reason,
                ref_id=ref_id,
            )
            response = Response(
                {
                    "status": result.status,
                    "farm_id": result.farm_id,
                    "daily_log_id": result.daily_log_id,
                    "fuel_log_id": result.fuel_log_id,
                    "expected_liters": str(result.expected_liters),
                    "actual_liters": str(result.actual_liters),
                    "variance_liters": str(result.variance_liters),
                    "posted_amount": str(result.posted_amount),
                }
            )
            self._commit_action_idempotency(
                request,
                key,
                object_id=f"fuel-reconciliation:{result.daily_log_id}:{result.fuel_log_id}",
                response=response,
            )
            return response
        except (ValueError, ValidationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
