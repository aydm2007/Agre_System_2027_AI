from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import IntegrityError

from .models_petty_cash import PettyCashRequest, PettyCashSettlement, PettyCashLine
from .services.petty_cash_service import PettyCashService
from .models_treasury import CashBox
from smart_agri.core.api.permissions import user_farm_ids, _ensure_user_has_farm_access
from smart_agri.core.api.viewsets.base import IdempotentCreateMixin
from smart_agri.core.permissions import StrictModeRequired


# --- Serializers ---

class PettyCashLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PettyCashLine
        fields = [
            'id', 'amount', 'description', 'date', 
            'budget_classification', 'related_daily_log', 'is_labor_settlement'
        ]


class PettyCashSettlementSerializer(serializers.ModelSerializer):
    lines = PettyCashLineSerializer(many=True, read_only=True)

    class Meta:
        model = PettyCashSettlement
        fields = [
            'id', 'request', 'status', 'total_expenses', 'refund_amount',
            'created_at', 'settled_by', 'settled_at', 'approval_note', 'lines'
        ]
        read_only_fields = ['status', 'total_expenses', 'refund_amount', 'settled_by', 'settled_at']


class PettyCashRequestSerializer(serializers.ModelSerializer):
    settlement = PettyCashSettlementSerializer(read_only=True)

    class Meta:
        model = PettyCashRequest
        fields = [
            'id', 'farm', 'requester', 'amount', 'description', 
            'cost_center', 'status', 'created_at', 'approved_by', 
            'approved_at', 'disbursed_transaction', 'settlement'
        ]
        read_only_fields = ['status', 'approved_by', 'approved_at', 'disbursed_transaction', 'requester']

    def create(self, validated_data):
        request = self.context['request']
        return PettyCashService.create_request(
            user=request.user,
            farm=validated_data['farm'],
            amount=validated_data['amount'],
            description=validated_data.get('description', ''),
            cost_center=validated_data.get('cost_center'),
        )


# --- ViewSets ---

class PettyCashRequestViewSet(IdempotentCreateMixin, viewsets.ModelViewSet):
    queryset = PettyCashRequest.objects.all()
    serializer_class = PettyCashRequestSerializer
    permission_classes = [permissions.IsAuthenticated, StrictModeRequired]
    enforce_idempotency = True

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(farm_id__in=user_farm_ids(self.request.user))
        if 'farm_id' in self.request.query_params:
            qs = qs.filter(farm_id=self.request.query_params['farm_id'])
        return qs

    def perform_create(self, serializer):
        farm = serializer.validated_data.get("farm")
        if farm:
            _ensure_user_has_farm_access(self.request.user, farm.id)
        serializer.instance = PettyCashService.create_request(
            user=self.request.user,
            farm=farm,
            amount=serializer.validated_data["amount"],
            description=serializer.validated_data.get("description", ""),
            cost_center=serializer.validated_data.get("cost_center"),
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser, StrictModeRequired])
    def approve(self, request, pk=None):
        """Approve the request for disbursement."""
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        try:
            pc_request = PettyCashService.approve_request(int(pk), request.user)
            response = Response(self.get_serializer(pc_request).data)
            self._commit_action_idempotency(request, key, object_id=str(pc_request.id), response=response)
            return response
        except (ValidationError, ObjectDoesNotExist, ValueError, TypeError, IntegrityError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser, StrictModeRequired])
    def disburse(self, request, pk=None):
        """Disburse the cash."""
        cash_box_id = request.data.get('cash_box_id')
        if not cash_box_id:
            return Response({"error": "cash_box_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        try:
            pc_request = PettyCashService.disburse_request(pk, cash_box_id, request.user)
            response = Response(self.get_serializer(pc_request).data)
            self._commit_action_idempotency(request, key, object_id=str(pc_request.id), response=response)
            return response
        except (ValidationError, ObjectDoesNotExist, ValueError, TypeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PettyCashSettlementViewSet(IdempotentCreateMixin, viewsets.ModelViewSet):
    queryset = PettyCashSettlement.objects.all()
    serializer_class = PettyCashSettlementSerializer
    permission_classes = [permissions.IsAuthenticated, StrictModeRequired]
    enforce_idempotency = True

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            farm_ids = user_farm_ids(self.request.user)
            qs = qs.filter(request__farm_id__in=farm_ids)
        farm_id = self.request.query_params.get('farm_id') or self.request.query_params.get('farm')
        if farm_id:
            qs = qs.filter(request__farm_id=farm_id)
        return qs

    def perform_create(self, serializer):
        request_obj = serializer.validated_data.get("request")
        if request_obj:
            _ensure_user_has_farm_access(self.request.user, request_obj.farm_id)
        settlement = PettyCashService.create_settlement(
            request_id=request_obj.id,
            user=self.request.user,
            approval_note=serializer.validated_data.get("approval_note", ""),
        )
        serializer.instance = settlement

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser, StrictModeRequired])
    def post_settlement(self, request, pk=None):
        """Settle the request, reversing suspense and posting actual expenses."""
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        try:
            settlement = PettyCashService.settle_request(pk, request.user)
            response = Response(self.get_serializer(settlement).data)
            self._commit_action_idempotency(request, key, object_id=str(settlement.id), response=response)
            return response
        except (ValidationError, ObjectDoesNotExist, ValueError, TypeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_line(self, request, pk=None):
        """Add an expense line to an un-posted settlement."""
        settlement = self.get_object()
        _ensure_user_has_farm_access(request.user, settlement.request.farm_id)
        if settlement.status != PettyCashSettlement.STATUS_PENDING:
            return Response({"error": "Cannot add lines to a posted settlement."}, status=status.HTTP_400_BAD_REQUEST)

        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        serializer = PettyCashLineSerializer(data=request.data)
        if serializer.is_valid():
            try:
                line = PettyCashService.add_settlement_line(
                    settlement_id=settlement.id,
                    user=request.user,
                    amount=serializer.validated_data["amount"],
                    description=serializer.validated_data["description"],
                    date=serializer.validated_data.get("date"),
                    budget_classification=serializer.validated_data.get("budget_classification"),
                )
            except (ValidationError, ObjectDoesNotExist, ValueError, TypeError, IntegrityError) as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            response = Response(PettyCashLineSerializer(line).data, status=status.HTTP_201_CREATED)
            self._commit_action_idempotency(request, key, object_id=str(line.id), response=response)
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
