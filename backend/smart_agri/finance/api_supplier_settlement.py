from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access, user_farm_ids
from smart_agri.core.api.viewsets.base import IdempotentCreateMixin
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.permissions import StrictModeRequired
from smart_agri.finance.models_supplier_settlement import SupplierSettlement
from smart_agri.finance.services.supplier_settlement_service import SupplierSettlementService


class SupplierSettlementSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="purchase_order.vendor_name", read_only=True)
    purchase_order_status = serializers.CharField(source="purchase_order.status", read_only=True)
    purchase_order_total_amount = serializers.DecimalField(
        source="purchase_order.total_amount",
        max_digits=19,
        decimal_places=4,
        read_only=True,
    )
    remaining_balance = serializers.DecimalField(max_digits=19, decimal_places=4, read_only=True)
    reconciliation_state = serializers.CharField(read_only=True)
    variance_severity = serializers.CharField(read_only=True)
    approval_state = serializers.CharField(source="status", read_only=True)
    visibility_level = serializers.SerializerMethodField()
    cost_display_mode = serializers.SerializerMethodField()
    policy_snapshot = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()

    class Meta:
        model = SupplierSettlement
        fields = [
            "id",
            "farm",
            "purchase_order",
            "purchase_order_status",
            "purchase_order_total_amount",
            "vendor_name",
            "invoice_reference",
            "due_date",
            "payment_method",
            "payable_amount",
            "paid_amount",
            "remaining_balance",
            "status",
            "approval_state",
            "reconciliation_state",
            "variance_severity",
            "cost_center",
            "crop_plan",
            "latest_treasury_transaction",
            "visibility_level",
            "cost_display_mode",
            "policy_snapshot",
            "payments",
            "rejected_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "farm",
            "payable_amount",
            "paid_amount",
            "remaining_balance",
            "status",
            "approval_state",
            "reconciliation_state",
            "variance_severity",
            "latest_treasury_transaction",
            "visibility_level",
            "cost_display_mode",
            "policy_snapshot",
            "payments",
        ]

    @staticmethod
    def _settings_for(obj):
        settings_obj = getattr(obj.farm, "settings", None)
        if settings_obj is not None:
            return settings_obj
        settings_obj, _ = FarmSettings.objects.get_or_create(farm=obj.farm)
        return settings_obj

    def get_visibility_level(self, obj):
        return self._settings_for(obj).visibility_level

    def get_cost_display_mode(self, obj):
        return self._settings_for(obj).cost_visibility

    def get_policy_snapshot(self, obj):
        return self._settings_for(obj).policy_snapshot()

    def get_payments(self, obj):
        return [
            {
                "id": payment.id,
                "amount": str(payment.amount),
                "treasury_transaction": payment.treasury_transaction_id,
                "reference": payment.treasury_transaction.reference,
                "created_at": payment.created_at,
            }
            for payment in obj.payments.select_related("treasury_transaction").filter(deleted_at__isnull=True)
        ]

    def create(self, validated_data):
        request = self.context["request"]
        return SupplierSettlementService.create_draft(
            user=request.user,
            purchase_order_id=validated_data["purchase_order"].id,
            invoice_reference=validated_data.get("invoice_reference", ""),
            due_date=validated_data.get("due_date"),
            payment_method=validated_data.get("payment_method", SupplierSettlement.PAYMENT_METHOD_CASH_BOX),
            cost_center=validated_data.get("cost_center"),
            crop_plan=validated_data.get("crop_plan"),
        )


class SupplierSettlementActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    cash_box_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(required=False, max_digits=19, decimal_places=4)
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    reference = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SupplierSettlementViewSet(IdempotentCreateMixin, viewsets.ModelViewSet):
    queryset = SupplierSettlement.objects.select_related(
        "farm__settings",
        "purchase_order",
        "latest_treasury_transaction",
        "cost_center",
        "crop_plan",
    ).all()
    serializer_class = SupplierSettlementSerializer
    permission_classes = [permissions.IsAuthenticated, StrictModeRequired]
    enforce_idempotency = True
    model_name = "SupplierSettlement"
    http_method_names = ["get", "post"]

    def get_queryset(self):
        qs = self.queryset.filter(deleted_at__isnull=True)
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(farm_id__in=user_farm_ids(user))

        farm_id = self.request.query_params.get("farm_id") or self.request.query_params.get("farm")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        return qs.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        purchase_order = request.data.get("purchase_order")
        if not purchase_order:
            return Response({"purchase_order": "purchase_order is required."}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        purchase_order = serializer.validated_data.get("purchase_order")
        if purchase_order:
            _ensure_user_has_farm_access(self.request.user, purchase_order.farm_id)
        serializer.instance = SupplierSettlementService.create_draft(
            user=self.request.user,
            purchase_order_id=purchase_order.id,
            invoice_reference=serializer.validated_data.get("invoice_reference", ""),
            due_date=serializer.validated_data.get("due_date"),
            payment_method=serializer.validated_data.get("payment_method", SupplierSettlement.PAYMENT_METHOD_CASH_BOX),
            cost_center=serializer.validated_data.get("cost_center"),
            crop_plan=serializer.validated_data.get("crop_plan"),
        )

    @action(detail=True, methods=["post"])
    def submit_review(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        settlement = SupplierSettlementService.submit_review(pk, request.user)
        response = Response(self.get_serializer(settlement).data)
        self._commit_action_idempotency(request, key, object_id=str(settlement.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        settlement = SupplierSettlementService.approve(pk, request.user)
        response = Response(self.get_serializer(settlement).data)
        self._commit_action_idempotency(request, key, object_id=str(settlement.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        serializer = SupplierSettlementActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settlement = SupplierSettlementService.reject(pk, request.user, serializer.validated_data.get("reason", ""))
        response = Response(self.get_serializer(settlement).data)
        self._commit_action_idempotency(request, key, object_id=str(settlement.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        settlement = SupplierSettlementService.reopen(pk, request.user)
        response = Response(self.get_serializer(settlement).data)
        self._commit_action_idempotency(request, key, object_id=str(settlement.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def record_payment(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        serializer = SupplierSettlementActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settlement = SupplierSettlementService.record_payment(
            settlement_id=pk,
            cash_box_id=serializer.validated_data["cash_box_id"],
            amount=serializer.validated_data["amount"],
            user=request.user,
            idempotency_key=key,
            note=serializer.validated_data.get("note", ""),
            reference=serializer.validated_data.get("reference", ""),
        )
        response = Response(self.get_serializer(settlement).data)
        self._commit_action_idempotency(request, key, object_id=str(settlement.id), response=response)
        return response
