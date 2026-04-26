import logging
import time
from datetime import date
from typing import Optional, Any
from django.db import connection, DatabaseError, IntegrityError
from django.db.models import F
from django.core.exceptions import ValidationError
from django.utils import timezone
from smart_agri.core.models import (
    LocationTreeStock, 
    Location, 
    CropVariety, 
    TreeProductivityStatus,
    Activity
)
from django.conf import settings

logger = logging.getLogger(__name__)

class TreeStockManager:
    """
    طبقة الوصول للبيانات لمخزون الأشجار.
    مسؤولة عن القفل والتحديث وتطبيق القيود على 'LocationTreeStock'.
    """
    
    DEFAULT_JUVENILE_YEARS = getattr(settings, "TREE_JUVENILE_YEARS", 3)
    DEFAULT_DECLINING_YEARS = getattr(settings, "TREE_DECLINING_YEARS", 18)

    def lock_existing_stock(self, stock: LocationTreeStock) -> LocationTreeStock:
        """
        الحصول على قفل سطر على سجل مخزون موجود.
        الوضع الصارم: يرفع DatabaseError إذا فشل القفل.
        """
        # AGRI-GUARDIAN: Replaced raw SQL with Django ORM for portability
        return LocationTreeStock.objects.select_for_update().get(pk=stock.pk)

    def lock_location_stock(self, activity: Activity) -> LocationTreeStock:
        """
        إيجاد أو إنشاء سجل مخزون لموقع/صنف النشاط مع القفل.
        """
        stock_qs = LocationTreeStock.objects.filter(location=activity.location, crop_variety=activity.variety)
        if connection.vendor == "postgresql":
            stock_qs = stock_qs.select_for_update()
        stock = stock_qs.first()
        if stock:
            # BIOLOGICAL INTEGRITY: Check Age Mixing
            # If we are adding new trees (delta > 0), ensure planting date matches or stock is generic.
            # If stock has a planting date 2010, and we try to add without specifying it (or imply new), 
            # we must BLOCK or split. Here we BLOCK for strictness.
            new_planting = activity.log.log_date if activity.tree_count_delta > 0 else None
            
            if new_planting and stock.planting_date and new_planting != stock.planting_date:
                 raise ValidationError({
                     "biological_integrity": f"Cannot mix trees planted in {new_planting} with existing stock planted in {stock.planting_date}. Use a different Location or Variety Batch."
                 })
                 
            return stock

        if activity.tree_count_delta < 0:
            raise ValidationError(
                {"tree_count_delta": "لا يمكن تخفيض عدد الأشجار قبل إنشاء رصيد للموقع في الجرد."}
            )

        status = self._default_productivity_status()
        planting_date = activity.log.log_date if activity.tree_count_delta > 0 else None
        
        # Note: concurrency safe create using fallback logic
        try:
            return LocationTreeStock.objects.create(
                location=activity.location,
                crop_variety=activity.variety,
                current_tree_count=0,
                productivity_status=status,
                planting_date=planting_date,
                source="",
            )
        except IntegrityError: 
            # IntegrityError (Race Condition)
            # Re-fetch the existing record with a lock
            fallback = (
                LocationTreeStock.objects.select_for_update()
                .filter(location=activity.location, crop_variety=activity.variety)
                .first()
            )
            if fallback is None:
                raise
            return fallback

    def apply_stock_delta(self, stock: LocationTreeStock, delta: Optional[int]) -> LocationTreeStock:
        """
        Apply tree count delta atomically with constraint check in the same query.
        """
        delta_value = int(delta or 0)
        if delta_value == 0:
            return stock

        # Atomic conditional update
        if delta_value < 0:
            updated_rows = LocationTreeStock.objects.filter(
                pk=stock.pk,
                current_tree_count__gte=-delta_value  # Ensures result >= 0
            ).update(
                current_tree_count=F("current_tree_count") + delta_value,
                updated_at=timezone.now()
            )
        else:
            updated_rows = LocationTreeStock.objects.filter(pk=stock.pk).update(
                current_tree_count=F("current_tree_count") + delta_value,
                updated_at=timezone.now()
            )

        if updated_rows == 0:
            stock.refresh_from_db()
            if stock.current_tree_count + delta_value < 0:
                raise ValidationError({
                    "tree_count_delta": "لا يمكن أن يصبح رصيد الأشجار أقل من صفر."
                })
            raise ValidationError({
                "stock": "فشل تحديث المخزون - السجل غير موجود أو تم تعديله."
            })

        stock.refresh_from_db()
        self._update_productivity_status(stock)
        stock.refresh_from_db()
        self._update_productivity_status(stock)
        return stock

    def update_stock_status(self, stock: LocationTreeStock, new_status: TreeProductivityStatus, user):
        """
        Updates tree lifecycle status.
        Agri-Guardian Rule: Death is final. No Zombie Trees.
        """
        if stock.productivity_status and stock.productivity_status.code in ['DEAD', 'REMOVED']:
            raise ValidationError(
                f"Cannot modify Tree Stock {stock.id}. It is permanently removed/dead."
            )

        # Proceed if alive
        stock.productivity_status = new_status
        # stock.updated_by = user # Assuming field exists or we just audit log it
        stock.save(update_fields=['productivity_status', 'updated_at'])
        return stock

    def _update_productivity_status(self, stock: LocationTreeStock):
        statuses = self._load_productivity_statuses()
        # Round 11 Fix: Avoid Timezone Schizophrenia
        target_status = self._determine_productivity_status(
            stock=stock,
            statuses=statuses,
            as_of=timezone.localdate(),
            current_count=stock.current_tree_count,
        )
        if target_status and getattr(target_status, "id", None) != stock.productivity_status_id:
            stock.productivity_status = target_status
            stock.save(update_fields=["productivity_status", "updated_at"])

    # --- Helpers ---
    
    def _default_productivity_status(self) -> Optional[TreeProductivityStatus]:
        try:
            return TreeProductivityStatus.objects.get(code="juvenile")
        except TreeProductivityStatus.DoesNotExist:
            return None

    def _load_productivity_statuses(self) -> dict[str, TreeProductivityStatus]:
        return {status.code: status for status in TreeProductivityStatus.objects.all()}

    def _age_thresholds(self) -> tuple[int, int]:
        juvenile = max(int(self.DEFAULT_JUVENILE_YEARS or 3), 1)
        declining = int(self.DEFAULT_DECLINING_YEARS or (juvenile + 10))
        if declining <= juvenile:
            declining = juvenile + 1
        return juvenile, declining

    def _determine_productivity_status(
        self,
        *,
        stock: LocationTreeStock,
        statuses: dict[str, TreeProductivityStatus],
        as_of: date,
        current_count: Optional[int] = None,
        planting_date: Optional[date] = None,
    ) -> Optional[TreeProductivityStatus]:
        count = stock.current_tree_count if current_count is None else current_count
        planting = stock.planting_date if planting_date is None else planting_date
        current_status = getattr(stock, "productivity_status", None)

        if count is None:
            count = 0
        if count <= 0:
            return statuses.get("dormant") or statuses.get("juvenile") or current_status

        if not planting:
            return current_status or statuses.get("productive") or statuses.get("juvenile")

        juvenile_years, declining_years = self._age_thresholds()

        if planting > as_of:
            return statuses.get("juvenile") or current_status

        age_days = (as_of - planting).days
        from decimal import Decimal, getcontext
        age_years = getcontext().divide(Decimal(str(age_days)), Decimal("365.25"))

        if age_years < juvenile_years:
            return statuses.get("juvenile") or current_status
        if age_years >= declining_years:
            return (
                statuses.get("declining")
                or statuses.get("productive")
                or current_status
            )
        return statuses.get("productive") or current_status
