"""
Variance Radar ViewSet — API for the Shadow Variance Dashboard.

Provides the HQ management team in Sana'a with:
- List all variance alerts (filterable by status, category, farm)
- Resolve alerts (mark as justified or penalized)

@idempotent
"""

from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from smart_agri.core.models.report import VarianceAlert
from smart_agri.core.api.serializers.variance import VarianceAlertSerializer


class VarianceRadarViewSet(viewsets.ModelViewSet):
    """
    [YECO Shadow ERP] رادار الانحرافات والمخاطر التشغيلية.

    واجهة برمجة تطبيقات مخصصة للإدارة العليا لمراقبة الهدر الميداني.

    @idempotent
    """
    queryset = VarianceAlert.objects.all().order_by('-created_at')
    serializer_class = VarianceAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        """Filter by status, category, and farm if query params provided."""
        queryset = super().get_queryset()

        # Filter by farm scope (tenant isolation)
        farm_id = self.request.query_params.get('farm')
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        category_filter = self.request.query_params.get('category')
        if category_filter:
            queryset = queryset.filter(category=category_filter)

        return queryset

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        قرار الإدارة حيال الهدر:
        - RESOLVED_JUSTIFIED: مبرر بسبب ظروف قاهرة
        - RESOLVED_PENALIZED: غير مُبرر — يتم تغريم المتسبب
        - UNDER_REVIEW: قيد المراجعة

        Required body: { "status": "...", "resolution_note": "..." }
        """
        alert = self.get_object()
        new_status = request.data.get('status')
        resolution_note = request.data.get('resolution_note', '')

        valid_transitions = {
            VarianceAlert.ALERT_STATUS_UNDER_REVIEW,
            VarianceAlert.ALERT_STATUS_RESOLVED_JUSTIFIED,
            VarianceAlert.ALERT_STATUS_RESOLVED_PENALIZED,
        }

        if new_status not in valid_transitions:
            return Response(
                {"error": f"🔴 حالة القرار غير صالحة. الخيارات المتاحة: {list(valid_transitions)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        alert.status = new_status
        alert.resolution_note = resolution_note
        if new_status.startswith('RESOLVED_'):
            alert.resolved_by = request.user
            alert.resolved_at = timezone.now()

        alert.save(update_fields=[
            'status', 'resolution_note', 'resolved_by', 'resolved_at',
        ])

        return Response({
            "status": "success",
            "message": f"تم إقفال حالة الإنذار لعملية ({alert.activity_name}) بنجاح.",
        }, status=status.HTTP_200_OK)
