"""
Partnerships API — Sharecropping, Touring, and Harvest endpoints.

@idempotent
"""

from decimal import Decimal, InvalidOperation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from smart_agri.core.models.partnerships import SharecroppingContract, TouringAssessment
from smart_agri.core.api.serializers.partnerships import (
    SharecroppingContractSerializer, TouringAssessmentSerializer,
)
from smart_agri.core.services.contract_operations_service import ContractOperationsService
from smart_agri.core.services.touring_harvest_service import TouringHarvestService


class SharecroppingContractViewSet(viewsets.ModelViewSet):
    """
    API for managing sharecropping/rental contracts.

    @idempotent
    """
    queryset = SharecroppingContract.objects.filter(
        deleted_at__isnull=True,
    ).select_related('farm', 'crop', 'season').order_by('-created_at')
    serializer_class = SharecroppingContractSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        farm_id = self.request.query_params.get('farm')
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        return queryset

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        farm_id = request.query_params.get('farm')
        payload = ContractOperationsService.build_dashboard(farm_id=farm_id)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def register_touring(self, request, pk=None):
        """
        تسجيل محضر الطواف (لجنة تقييم ما قبل الحصاد).

        Required body:
        {
            "estimated_kg": "5000.0000",
            "committee_members": ["محمد أحمد", "علي سعيد", "عبدالله حسن"]
        }
        """
        try:
            estimated_kg = Decimal(str(request.data.get('estimated_kg', '0')))
            committee = request.data.get('committee_members', [])

            assessment = TouringHarvestService.execute_touring_assessment(
                contract_id=int(pk),
                estimated_kg=estimated_kg,
                committee=committee,
            )

            serializer = TouringAssessmentSerializer(assessment)
            return Response({
                "message": "تم تسجيل محضر الطواف بنجاح واعتماد حصة المؤسسة التقديرية.",
                "assessment": serializer.data,
            }, status=status.HTTP_201_CREATED)

        except (ValueError, InvalidOperation) as e:
            return Response(
                {"error": f"قيمة رقمية غير صالحة: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (ValidationError, OperationalError, PermissionDenied) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=['post'])
    def process_harvest(self, request, pk=None):
        """
        تنفيذ الحصاد واقتطاع الزكاة وحصة المؤسسة.

        Required body:
        {
            "actual_kg": "4800.0000",
            "yield_type": "IN_KIND",  // or "CASH"
            "committee_members": ["محمد أحمد", "علي سعيد", "عبدالله حسن"]
        }
        """
        try:
            actual_kg = Decimal(str(request.data.get('actual_kg', '0')))
            yield_type = request.data.get('yield_type')
            committee = request.data.get('committee_members', [])

            result = TouringHarvestService.execute_sharecropping_harvest(
                contract_id=int(pk),
                actual_total_kg=actual_kg,
                yield_type=yield_type,
                committee=committee,
            )

            return Response(result, status=status.HTTP_200_OK)

        except (ValueError, InvalidOperation) as e:
            return Response(
                {"error": f"قيمة رقمية غير صالحة: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (ValidationError, OperationalError, PermissionDenied) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=['post'], url_path='record-rent-payment')
    def record_rent_payment(self, request, pk=None):
        try:
            result = ContractOperationsService.record_rent_payment(
                contract_id=int(pk),
                amount=request.data.get('amount', '0'),
                payment_period=request.data.get('payment_period', ''),
                notes=request.data.get('notes', ''),
                user=request.user,
            )
            return Response(result, status=status.HTTP_200_OK)
        except PermissionDenied as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except (ValidationError, InvalidOperation, ValueError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class TouringAssessmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for viewing touring assessments.

    @idempotent
    """
    queryset = TouringAssessment.objects.select_related(
        'contract__farm', 'contract',
    ).order_by('-assessment_date')
    serializer_class = TouringAssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        farm_id = self.request.query_params.get('farm')
        if farm_id:
            queryset = queryset.filter(contract__farm_id=farm_id)
        contract_id = self.request.query_params.get('contract')
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)
        return queryset

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from smart_agri.core.models.partnerships import SharecroppingReceipt
from smart_agri.core.api.serializers.partnerships import SharecroppingReceiptSerializer

class SharecroppingReceiptViewSet(viewsets.ModelViewSet):
    """
    API for Sharecropping Receipts (Financial or Physical).
    @idempotent
    """
    queryset = SharecroppingReceipt.objects.select_related(
        'farm', 'assessment__contract', 'destination_inventory', 'received_by'
    ).order_by('-receipt_date')
    serializer_class = SharecroppingReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['receipt_type', 'is_posted', 'farm_id']
    search_fields = ['assessment__contract__farmer_name', 'notes']
    ordering_fields = ['receipt_date', 'amount_received', 'quantity_received_kg']

    def get_queryset(self):
        queryset = super().get_queryset()
        farm_id = self.request.query_params.get('farm')
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
        return queryset

