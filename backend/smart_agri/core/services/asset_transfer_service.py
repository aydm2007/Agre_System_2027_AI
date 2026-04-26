import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from smart_agri.core.models.farm import AssetTransfer, Asset

logger = logging.getLogger(__name__)

class AssetTransferService:
    @staticmethod
    @transaction.atomic
    def request_transfer(asset_id: int, to_farm_id: int, user, justification: str) -> AssetTransfer:
        asset = Asset.objects.select_for_update().filter(pk=asset_id).first()
        if not asset:
            raise ValidationError("Asset not found.")
            
        if asset.farm_id == to_farm_id:
            raise ValidationError("Asset is already in the target farm.")

        # Check for existing pending transfers
        pending_transfer = AssetTransfer.objects.filter(
            asset=asset, status=AssetTransfer.STATUS_PENDING
        ).first()
        
        if pending_transfer:
            raise ValidationError(
                f"A pending transfer request already exists for this asset to farm: {pending_transfer.to_farm.name}"
            )

        transfer = AssetTransfer.objects.create(
            asset=asset,
            from_farm=asset.farm,
            to_farm_id=to_farm_id,
            justification=justification,
            requested_by=user,
        )
        
        logger.info(f"Asset Transfer requested: {asset.name} from Farm {asset.farm_id} to Farm {to_farm_id}")
        return transfer

    @staticmethod
    @transaction.atomic
    def approve_transfer(transfer_id: int, user) -> AssetTransfer:
        transfer = AssetTransfer.objects.select_for_update().get(pk=transfer_id)
        if transfer.status != AssetTransfer.STATUS_PENDING:
            raise ValidationError("Only pending transfers can be approved.")
            
        # Optional: Add Authority Check here if we want to restrict approval to superusers/finance admins
        
        # 1. Update Asset Farm Location
        asset = transfer.asset
        asset.farm = transfer.to_farm
        asset.save(update_fields=['farm', 'updated_at'])
        
        # 2. Update Transfer Status
        transfer.status = AssetTransfer.STATUS_APPROVED
        transfer.approved_by = user
        transfer.approved_at = timezone.now()
        transfer.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        
        # [Axis 7] Audit Logging
        from smart_agri.core.models.log import AuditLog
        AuditLog.objects.create(
            action='ASSET_TRANSFERRED',
            model='Asset',
            object_id=str(asset.id),
            actor=user,
            new_payload={
                'asset_name': asset.name,
                'from_farm_id': transfer.from_farm_id,
                'to_farm_id': transfer.to_farm_id,
                'transfer_request_id': transfer.id
            },
        )
        
        logger.info(f"Asset Transfer APPROVED: {asset.name} moved to Farm {transfer.to_farm.name}")
        return transfer

    @staticmethod
    @transaction.atomic
    def reject_transfer(transfer_id: int, user, reason: str) -> AssetTransfer:
        transfer = AssetTransfer.objects.select_for_update().get(pk=transfer_id)
        if transfer.status != AssetTransfer.STATUS_PENDING:
            raise ValidationError("Only pending transfers can be rejected.")
            
        if not reason or not reason.strip():
            raise ValidationError("Rejection reason must be provided.")
            
        transfer.status = AssetTransfer.STATUS_REJECTED
        transfer.rejection_reason = reason
        transfer.approved_by = user
        transfer.approved_at = timezone.now()
        transfer.save(update_fields=['status', 'rejection_reason', 'approved_by', 'approved_at', 'updated_at'])
        
        logger.info(f"Asset Transfer REJECTED: {transfer.asset.name}")
        return transfer
