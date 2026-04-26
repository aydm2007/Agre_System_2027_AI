from rest_framework import permissions, viewsets
from rest_framework.response import Response

from smart_agri.core.services.fixed_asset_workflow_service import FixedAssetWorkflowService


class FixedAssetsDashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        payload = FixedAssetWorkflowService.build_dashboard_payload(
            user=request.user,
            farm_id=request.query_params.get("farm_id") or request.headers.get("X-Farm-ID"),
            category=request.query_params.get("category"),
        )
        return Response(payload)
