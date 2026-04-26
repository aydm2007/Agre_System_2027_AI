from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from smart_agri.finance.models import WorkerAdvance
from smart_agri.core.api.permissions import user_farm_ids
from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.core.permissions import StrictModeRequired
from smart_agri.finance.services.advances_service import WorkerAdvanceService

class WorkerAdvanceSerializer(serializers.ModelSerializer):
    worker_name = serializers.CharField(source='worker.first_name', read_only=True)
    supervisor_name = serializers.CharField(source='supervisor.username', read_only=True)
    
    class Meta:
        model = WorkerAdvance
        fields = [
            'id', 'worker', 'worker_name', 'amount', 'date', 
            'supervisor', 'supervisor_name', 'notes', 'is_deducted'
        ]
        read_only_fields = ['supervisor', 'date', 'is_deducted']

class WorkerAdvanceViewSet(AuditedModelViewSet):
    """
    [AGRI-GUARDIAN] Manage Daily Cash Advances (Salif).
    Supervisors can issue, Admins can view/deduct.
    """
    queryset = WorkerAdvance.objects.all().order_by('-date')
    serializer_class = WorkerAdvanceSerializer
    enforce_idempotency = True
    permission_classes = [permissions.IsAuthenticated, StrictModeRequired]

    def get_queryset(self):
        qs = super().get_queryset().select_related('worker', 'worker__farm', 'supervisor')
        user = self.request.user
        if user.is_superuser:
            return qs
        allowed_farms = user_farm_ids(user)
        return qs.filter(worker__farm_id__in=allowed_farms)

    def perform_create(self, serializer):
        worker = serializer.validated_data.get('worker')
        serializer.instance = WorkerAdvanceService.create_advance(
            user=self.request.user,
            worker=worker,
            amount=serializer.validated_data.get('amount'),
            notes=serializer.validated_data.get('notes', ''),
        )

    @action(detail=False, methods=['get'])
    def my_advances(self, request):
        """View advances for the logged-in worker (if applicable)"""
        # Assuming User <-> Employee OneToOne exists
        if hasattr(request.user, 'employee_profile'):
            advances = self.get_queryset().filter(worker=request.user.employee_profile)
            serializer = self.get_serializer(advances, many=True)
            return Response(serializer.data)
        return Response({"error": "Not a worker"}, status=400)

    @action(detail=False, methods=['get'])
    def outstanding(self, request):
        """View total outstanding advances for payroll"""
        qs = self.get_queryset().filter(is_deducted=False)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
