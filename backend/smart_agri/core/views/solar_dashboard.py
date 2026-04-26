from rest_framework import viewsets, permissions
from rest_framework.response import Response
from decimal import Decimal
from smart_agri.core.models.farm import SolarAsset
from smart_agri.core.models.rls_scope import get_rls_user_id

class SolarFleetViewSet(viewsets.ViewSet):
    """
    [AGRI-GUARDIAN] Read-Only ViewSet for Solar Fleet Monitoring Dashboard
    Provides consolidated metadata and depreciation status for Solar Assets.
    Route: GET /api/v1/core/solar-fleet/
    """
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        # 1. Enforce Farm Scoping via RLS middleware
        # We use the SolarAsset Proxy Model which filters category="Solar".
        queryset = SolarAsset.objects.all().select_related('farm')
        
        # [AGRI-GUARDIAN §Axis-6] RLS: Scope to user's farms via membership
        rls_user_id = get_rls_user_id()
        if rls_user_id and rls_user_id != -1:
            queryset = queryset.filter(farm__memberships__user_id=rls_user_id).distinct()
        
        # 2. Add explicit support for `farm_id` if present in headers or query params
        farm_id = request.headers.get('X-Farm-ID') or request.query_params.get('farm_id')
        if farm_id:
            queryset = queryset.filter(farm_id=farm_id)
            
        assets_data = []
        for asset in queryset:
            purchase_val = Decimal(str(asset.purchase_value or 0))
            salvage_val = Decimal(str(asset.salvage_value or 0))
            accumulated = Decimal(str(asset.accumulated_depreciation or 0))
            
            depreciable_base = purchase_val - salvage_val
            
            percentage = Decimal(0)
            if depreciable_base > 0:
                percentage = (accumulated / depreciable_base) * Decimal('100')
            
            # Determine visual health status based on percentage
            health_status = 'GREEN'
            if percentage >= Decimal('90'):
                health_status = 'CRITICAL'
            elif percentage >= Decimal('70'):
                health_status = 'WARNING'
                
            useful_life_hours = Decimal(max(0, asset.useful_life_years)) * Decimal('365') * Decimal('24')
                
            assets_data.append({
                'id': asset.id,
                'name': asset.name,
                'code': asset.code,
                'status': asset.status,
                'farm_name': asset.farm.name,
                'health_status': health_status,
                'depreciation_percentage': str(percentage.quantize(Decimal('0.01'))),
                'accumulated_depreciation': str(accumulated.quantize(Decimal('0.0001'))),
                'purchase_value': str(purchase_val),
                'useful_life_years': asset.useful_life_years,
                'useful_life_hours': str(useful_life_hours),
            })
            
        return Response({
            'count': len(assets_data),
            'results': assets_data
        })
