from rest_framework import filters as rf_filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters import rest_framework as df_filters

from smart_agri.finance.api_ledger import FinancialLedgerSerializer, LedgerFilter
from smart_agri.finance.api_ledger_support import (
    build_ledger_queryset_for_user,
    summarize_ledger_queryset,
)


class ShadowLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    SIMPLE/STRICT read-only shadow ledger surface.

    Uses the same ledger truth chain and queryset shaping as the governed
    finance ledger, but is mounted outside the `/finance/ledger/` route tree
    so SIMPLE mode can inspect append-only daily entries without reopening
    strict authoring surfaces.
    """

    http_method_names = ["get", "head", "options"]
    serializer_class = FinancialLedgerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        rf_filters.SearchFilter,
        rf_filters.OrderingFilter,
        df_filters.DjangoFilterBackend,
    ]
    filterset_class = LedgerFilter
    ordering = ["-created_at"]
    ordering_fields = ["created_at", "debit", "credit", "account_code", "id"]

    def get_queryset(self):
        return build_ledger_queryset_for_user(request=self.request, user=self.request.user)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.filter_queryset(self.get_queryset())
        return Response(summarize_ledger_queryset(qs))
