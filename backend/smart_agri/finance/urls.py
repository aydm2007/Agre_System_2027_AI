from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from smart_agri.finance.api import router


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def overhead_allocation_view(request):
    """POST /api/v1/finance/overhead-allocate/ — Distribute overhead to crop plans."""
    from smart_agri.core.services.overhead_allocation_service import OverheadAllocationService
    farm_id = request.data.get('farm_id') or request.query_params.get('farm')
    year = int(request.data.get('year', 0) or 0)
    month = int(request.data.get('month', 0) or 0)
    
    idempotency_key = request.headers.get("X-Idempotency-Key") or request.META.get("HTTP_X_IDEMPOTENCY_KEY")
    if not idempotency_key:
        return Response({"detail": "مطلوب ترويسة X-Idempotency-Key لضمان عدم تكرار العملية."}, status=status.HTTP_400_BAD_REQUEST)

    if not all([farm_id, year, month]):
        return Response({"detail": "farm_id, year, month مطلوبة."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        result = OverheadAllocationService.allocate_monthly_overhead(
            farm_id=farm_id, year=year, month=month, actor=request.user,
        )
        return Response(result)
    except (ValueError, TypeError, LookupError) as e:
        import logging
        logging.getLogger(__name__).exception("API Error in overhead_allocation_view")
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def variance_analysis_view(request):
    """GET /api/v1/finance/variance-analysis/ — Price & Quantity variance report."""
    from smart_agri.core.services.variance_analysis_service import VarianceAnalysisService
    farm_id = request.query_params.get('farm')
    crop_plan_id = request.query_params.get('crop_plan_id')
    season_id = request.query_params.get('season_id')
    result = VarianceAnalysisService.get_variance_report(
        farm_id=farm_id, crop_plan_id=crop_plan_id, season_id=season_id,
    )
    return Response(result)


from smart_agri.finance.api_reports import profitability_summary_view, trial_balance_view

urlpatterns = [
    path("", include(router.urls)),
    path("overhead-allocate/", overhead_allocation_view, name="overhead-allocate"),
    path("variance-analysis/", variance_analysis_view, name="variance-analysis"),
    path("profitability-summary/", profitability_summary_view, name="profitability-summary"),
    path("trial-balance/", trial_balance_view, name="trial-balance"),
]
