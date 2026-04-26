"""
خدمة الاستعلامات لمخزون الأشجار.

خدمة للقراءة فقط (Read-Only) توفر استعلامات محسنة لبيانات مخزون الأشجار.
لا تقوم بأي تعديلات على البيانات.

FORENSIC AUDIT REFACTORING (2026-01-24): Phase 4 - Architectural Refactoring
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce

from smart_agri.core.models import (
    LocationTreeStock,
    TreeStockEvent,
    TreeServiceCoverage,
    Location,
    CropVariety,
)

logger = logging.getLogger(__name__)


class TreeQueryService:
    """
    خدمة استعلامات مخزون الأشجار (Read-Only).
    
    توفر طرقاً محسنة للاستعلام عن بيانات المخزون والأحداث والتغطيات
    دون إجراء أي تعديلات على البيانات.
    """

    def get_stock_summary(
        self,
        location: Location,
        variety: Optional[CropVariety] = None,
    ) -> Dict[str, Any]:
        """
        الحصول على ملخص المخزون لموقع معين.
        
        المعاملات:
            location: الموقع المطلوب
            variety: الصنف (اختياري، إذا لم يُحدد يُرجع جميع الأصناف)
            
        الإرجاع:
            قاموس يحتوي على إجمالي الأشجار وتوزيعها حسب الحالة
        """
        qs = LocationTreeStock.objects.filter(location=location)
        if variety:
            qs = qs.filter(crop_variety=variety)
        
        summary = qs.aggregate(
            total_trees=Coalesce(Sum('current_tree_count'), 0),
            stock_records=Count('id'),
        )
        
        # توزيع حسب حالة الإنتاجية
        status_distribution = list(
            qs.values('productivity_status__code', 'productivity_status__name')
            .annotate(count=Sum('current_tree_count'))
            .order_by('-count')
        )
        
        summary['status_distribution'] = status_distribution
        return summary

    def get_stock_by_variety(
        self,
        location: Location,
    ) -> List[Dict[str, Any]]:
        """
        الحصول على مخزون الأشجار مجمّع حسب الصنف.
        """
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

    def get_recent_events(
        self,
        location: Location,
        variety: Optional[CropVariety] = None,
        limit: int = 20,
    ) -> List[TreeStockEvent]:
        """
        الحصول على آخر أحداث المخزون لموقع معين.
        """
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

    def get_harvest_totals(
        self,
        location: Location,
        variety: Optional[CropVariety] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Decimal]:
        """
        الحصول على إجمالي الحصاد لموقع معين.
        """
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

    def get_service_coverage_summary(
        self,
        location: Location,
        activity_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        الحصول على ملخص تغطية الخدمات لموقع معين.
        """
        qs = TreeServiceCoverage.objects.filter(location=location)
        if activity_id:
            qs = qs.filter(activity_id=activity_id)
        
        return qs.aggregate(
            total_serviced=Coalesce(Sum('service_count'), 0),
            coverage_records=Count('id'),
        )

    def find_stock(
        self,
        location: Location,
        variety: CropVariety,
    ) -> Optional[LocationTreeStock]:
        """
        البحث عن سجل مخزون محدد.
        """
        return LocationTreeStock.objects.filter(
            location=location,
            crop_variety=variety,
        ).first()

    def check_stock_exists(
        self,
        location: Location,
        variety: CropVariety,
    ) -> bool:
        """
        التحقق من وجود سجل مخزون.
        """
        return LocationTreeStock.objects.filter(
            location=location,
            crop_variety=variety,
        ).exists()

    def get_locations_with_stock(
        self,
        farm_id: int,
        min_tree_count: int = 1,
    ) -> List[Location]:
        """
        الحصول على المواقع التي تحتوي على مخزون أشجار.
        """
        location_ids = (
            LocationTreeStock.objects.filter(
                location__farm_id=farm_id,
                current_tree_count__gte=min_tree_count,
            )
            .values_list('location_id', flat=True)
            .distinct()
        )
        return list(Location.objects.filter(id__in=location_ids))
