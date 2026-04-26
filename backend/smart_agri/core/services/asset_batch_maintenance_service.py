import logging
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from smart_agri.core.models.farm import AssetBatchMaintenance, AssetBatchMaintenanceLine, Asset
from smart_agri.core.services.maintenance_service import MaintenanceService

logger = logging.getLogger(__name__)

class AssetBatchMaintenanceService:
    """
    [AGRI-GUARDIAN Phase 5] Batch Maintenance Service.
    Handles the aggregation of machine spare parts and labors into a single ledger hit.
    """

    @staticmethod
    @transaction.atomic
    def approve_batch(batch_id: int, user) -> AssetBatchMaintenance:
        batch = AssetBatchMaintenance.objects.select_for_update().get(pk=batch_id)
        
        if batch.status != AssetBatchMaintenance.STATUS_DRAFT:
            raise ValidationError("Only draft maintenance batches can be approved.")
            
        farm_id = batch.farm_id
        asset = batch.asset
        
        lines = list(batch.lines.all())
        if not lines:
            raise ValidationError("Cannot approve an empty maintenance batch.")
            
        total_cost = sum(line.cost for line in lines)
        if total_cost <= Decimal("0.00"):
            raise ValidationError("Total maintenance cost must be greater than zero.")
            
        batch.total_cost = total_cost
        
        # Build composite description
        line_desc = " | ".join([f"{line.description} ({line.cost})" for line in lines])
        full_desc = f"{batch.description} - Details: {line_desc}"
        
        # [Axis 4 & 5] Call the existing MaintenanceService to hit the Financial Ledger
        # MaintenanceService handles the double-entry (DR Maintenance Expense, CR Cash)
        # We pass it as a CORRECTIVE maintenance by default, or we can make it an argument.
        
        result = MaintenanceService.record_maintenance(
            asset_id=asset.id,
            cost=total_cost,
            description=full_desc[:255], # Ensure we don't exceed max_length
            farm_id=farm_id,
            maintenance_type='CORRECTIVE',
            user=user,
        )
        
        # Mark as approved
        batch.status = AssetBatchMaintenance.STATUS_APPROVED
        batch.approved_by = user
        batch.approved_at = timezone.now()
        batch.save(update_fields=['total_cost', 'status', 'approved_by', 'approved_at', 'updated_at'])
        
        logger.info(f"Batch Maintenance {batch.id} for {asset.name} approved with total cost: {total_cost}")
        
        return batch
