from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import date
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from smart_agri.core.models.farm import Location
from smart_agri.core.models.crop import CropVariety
from smart_agri.core.models.tree import (
    LocationTreeStock,
    TreeStockEvent,
    TreeServiceCoverage
)

class TreeSelectors:
    """
    Read-Only Query Interface for Tree Inventory.
    Separated from TreeInventoryService (Command) to enforce CQS Pattern.
    """

    @staticmethod
    def get_stock_summary(
        location: Location,
        variety: Optional[CropVariety] = None,
    ) -> Dict[str, Any]:
        """Get summary of tree stock for a location."""
        qs = LocationTreeStock.objects.filter(location=location)
        if variety:
            qs = qs.filter(crop_variety=variety)
        
        summary = qs.aggregate(
            total_trees=Coalesce(Sum('current_tree_count'), 0),
            stock_records=Count('id'),
        )
        
        # Distribution by Productivity Status
        status_distribution = list(
            qs.values('productivity_status__code', 'productivity_status__name_en', 'productivity_status__name_ar')
            .annotate(count=Sum('current_tree_count'))
            .order_by('-count')
        )
        
        summary['status_distribution'] = status_distribution
        return summary

    @staticmethod
    def get_stock_by_variety(
        location: Location,
    ) -> List[Dict[str, Any]]:
        """Get stock grouped by variety."""
        return list(
            LocationTreeStock.objects.filter(location=location)
            .values(
                'crop_variety__id',
                'crop_variety__name',
                'productivity_status__code',
            )
            .annotate(
                tree_count=Sum('current_tree_count'),
            )
            .order_by('crop_variety__name')
        )

    @staticmethod
    def get_recent_events(
        location: Location,
        variety: Optional[CropVariety] = None,
        limit: int = 20,
    ) -> List[TreeStockEvent]:
        """Get recent events audit trail."""
        qs = TreeStockEvent.objects.filter(
            location_tree_stock__location=location
        ).select_related(
            'location_tree_stock__crop_variety',
            'activity',
            'loss_reason',
        ).order_by('-created_at')
        
        if variety:
            qs = qs.filter(location_tree_stock__crop_variety=variety)
        
        return list(qs[:limit])

    @staticmethod
    def get_harvest_totals(
        location: Location,
        variety: Optional[CropVariety] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Decimal]:
        """Get harvest aggregate data."""
        qs = TreeStockEvent.objects.filter(
            location_tree_stock__location=location,
            event_type=TreeStockEvent.HARVEST,
        )
        
        if variety:
            qs = qs.filter(location_tree_stock__crop_variety=variety)
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
        
        result = qs.aggregate(
            total_quantity=Coalesce(Sum('harvest_quantity'), Decimal('0')),
            harvest_count=Count('id'),
        )
        return result

    @staticmethod
    def get_service_coverage_summary(
        location: Location,
        activity_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get service coverage stats."""
        qs = TreeServiceCoverage.objects.filter(location=location)
        if activity_id:
            qs = qs.filter(activity_id=activity_id)
        
        return qs.aggregate(
            total_serviced=Coalesce(Sum('trees_covered'), 0),
            coverage_records=Count('id'),
        )
