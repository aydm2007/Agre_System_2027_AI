"""
[AGRI-GUARDIAN] Treasury / Cash Management API
Extracted from finance/api.py for maintainability.
"""
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from smart_agri.core.permissions import StrictModeRequired
from rest_framework.exceptions import ValidationError as DRFValidationError

from smart_agri.core.api.viewsets.base import IdempotentCreateMixin
from smart_agri.core.api.permissions import (
    user_farm_ids,
    _ensure_user_has_farm_access,
    user_has_farm_role,
)
from smart_agri.core.throttles import FinancialMutationThrottle
from smart_agri.finance.models_treasury import CashBox, TreasuryTransaction
from smart_agri.finance.serializers import CashBoxSerializer, TreasuryTransactionSerializer
from smart_agri.finance.services.core_finance import FinanceService
from smart_agri.finance.services.treasury_service import TreasuryService


# ─── ViewSets ────────────────────────────────────────────────────────────────

class CashBoxViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only cash boxes.

    Balances are mutated ONLY via append-only `TreasuryTransaction` postings.
    """

    serializer_class = CashBoxSerializer
    permission_classes = [IsAuthenticated]
    ordering = ["name"]

    def get_queryset(self):
        user = self.request.user
        qs = CashBox.objects.filter(deleted_at__isnull=True, is_active=True).select_related("farm")
        if not user.is_superuser:
            allowed_farms = user_farm_ids(user)
            qs = qs.filter(farm_id__in=allowed_farms)

        farm_id = self.request.query_params.get("farm_id") or self.request.query_params.get("farm")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)

        return qs.order_by("name")


class TreasuryTransactionViewSet(
    IdempotentCreateMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Append-only treasury transactions.

    - Requires `X-Idempotency-Key` for network idempotency.
    - Requires `X-Farm-Id` to pin the mutation to a specific farm scope.
    - Never trusts client payload for `farm` / `idempotency_key`.
    """

    enforce_idempotency = True
    serializer_class = TreasuryTransactionSerializer
    permission_classes = [IsAuthenticated, StrictModeRequired]
    throttle_classes = [FinancialMutationThrottle]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = (
            TreasuryTransaction.objects.filter(deleted_at__isnull=True)
            .select_related("farm", "cash_box")
            .order_by("-created_at")
        )

        if not user.is_superuser:
            allowed_farms = user_farm_ids(user)
            qs = qs.filter(farm_id__in=allowed_farms)

        farm_id = self.request.query_params.get("farm_id") or self.request.query_params.get("farm")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)

        return qs

    def perform_create(self, serializer):
        user = self.request.user

        farm_header = self.request.headers.get("X-Farm-Id") or self.request.headers.get("X-Farm-ID")
        if not farm_header:
            raise DRFValidationError("ترويسة X-Farm-Id مطلوبة لعمليات الخزينة.")

        try:
            farm_id = int(str(farm_header).strip())
        except ValueError as exc:
            raise DRFValidationError("قيمة X-Farm-Id يجب أن تكون رقم مزرعة صحيحًا.") from exc

        if not (user.is_superuser or user.has_perm("finance.can_post_treasury")):
            if not user_has_farm_role(user, farm_id, {"Admin", "Manager"}):
                raise DRFValidationError("عملية الخزينة تتطلب صلاحية مالية معتمدة.")

        _ensure_user_has_farm_access(user, farm_id)

        # Idempotency checks are now handled by IdempotentCreateMixin (V2)
        header_key = self.request.headers.get("X-Idempotency-Key") or self.request.headers.get("HTTP_X_IDEMPOTENCY_KEY")

        cash_box = serializer.validated_data.get("cash_box")
        if cash_box and cash_box.farm_id != farm_id:
            raise DRFValidationError({"cash_box": "الصندوق النقدي يجب أن ينتمي إلى المزرعة النشطة."})

        FinanceService.check_fiscal_period(
            serializer.validated_data.get("date"),
            cash_box.farm if cash_box else serializer.validated_data.get("farm"),
            strict=True,
        )

        serializer.instance = TreasuryService.create_transaction(
            user=user,
            farm_id=farm_id,
            idempotency_key=header_key,
            **serializer.validated_data,
        )
