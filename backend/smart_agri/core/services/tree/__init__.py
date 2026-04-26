"""
حزمة خدمات إدارة الأشجار (Tree Services Package).

FORENSIC AUDIT REFACTORING (2026-01-24):
تم تقسيم الخدمة الضخمة TreeInventoryService إلى خدمات متخصصة:
- TreeEventCalculator: حساب أنواع الأحداث
- TreeStockManager: إدارة مخزون الأشجار
- TreeServiceCoverageService: إدارة تغطية الخدمات
- TreeQueryService: استعلامات القراءة فقط
"""

from .event_calculator import TreeEventCalculator
from .stock_manager import TreeStockManager
from .coverage_service import TreeServiceCoverageService
from .query_service import TreeQueryService

__all__ = [
    'TreeEventCalculator',
    'TreeStockManager',
    'TreeServiceCoverageService',
    'TreeQueryService',
]
