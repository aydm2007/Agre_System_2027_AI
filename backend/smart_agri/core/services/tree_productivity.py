import logging
import time
from datetime import date
from typing import Optional

from django.db import transaction
from django.utils import timezone

from smart_agri.core.models import LocationTreeStock
# IMPORT FROM SAME PACKAGE
from .tree_inventory import TreeStockManager

logger = logging.getLogger(__name__)


class TreeProductivityService:
    """
    Service responsible for managing tree productivity status updates.
    Flattened from services.tree.productivity.
    """

    def refresh_productivity_status(
        self,
        *,
        queryset=None,
        batch_size: int = 200,
        as_of: Optional[date] = None,
    ) -> dict[str, float | int]:
        """تحديث حالة الإنتاجية لجميع السجلات أو مجموعة محددة منها."""

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        stock_manager = TreeStockManager()
        stock_qs = queryset or LocationTreeStock.objects.all()
        stock_qs = stock_qs.order_by("pk")

        processed = 0
        updated = 0
        skipped = 0
        start_time = time.perf_counter()

        last_pk: int | None = None
        while True:
            window = stock_qs
            if last_pk is not None:
                window = window.filter(pk__gt=last_pk)
            batch_ids = list(window.values_list("pk", flat=True)[:batch_size])
            if not batch_ids:
                break

            with transaction.atomic():
                stocks = list(
                    LocationTreeStock.objects.select_for_update()
                    .filter(pk__in=batch_ids)
                    .order_by("pk")
                )
                
                stocks_to_update = []
                
                # FORENSIC FIX: Cache statuses once to avoid N+1 query
                cached_statuses = stock_manager._load_productivity_statuses()
                for stock in stocks:
                    try:
                        # status check
                        target_status = stock_manager._determine_productivity_status(
                            stock=stock,
                            statuses=cached_statuses,
                            as_of=as_of or date.today(),
                        )
                        
                        if target_status and target_status.pk != stock.productivity_status_id:
                            stock.productivity_status = target_status
                            stock.updated_at = timezone.now()
                            stocks_to_update.append(stock)
                            updated += 1 
                        else:
                            skipped += 1
                    except (ValidationError, ValueError, ZeroDivisionError) as e:
                        # POISON PILL PROTECTION: Log error and continue, don't crash batch.
                        logger.error(f"Failed to refresh stock {stock.pk}: {e}", exc_info=True)
                        continue

                if stocks_to_update:
                    LocationTreeStock.objects.bulk_update(
                        stocks_to_update,
                        ['productivity_status', 'updated_at'],
                        batch_size=batch_size
                    )
            
            processed += len(stocks)
            last_pk = batch_ids[-1]

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Refreshed tree productivity statuses",
            extra={
                "processed": processed,
                "updated": updated,
                "skipped": skipped,
                "elapsed_seconds": round(elapsed, 3),
            },
        )
        return {
            "processed": processed,
            "updated": updated,
            "skipped": skipped,
            "elapsed": elapsed,
        }
