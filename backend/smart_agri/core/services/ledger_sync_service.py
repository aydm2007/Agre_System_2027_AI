"""
Ledger Sync Service - Extracted from ActivityService (God Object Refactoring).

AGRI-GUARDIAN: Single Responsibility for Financial Ledger synchronization.
"""
from decimal import Decimal
from django.db import models, transaction
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class LedgerSyncService:
    """
    Dedicated service for synchronizing activity costs with the financial ledger.
    Extracted from ActivityService for better maintainability.
    """

    @staticmethod
    @transaction.atomic
    def sync_activity_ledger(activity, user):
        """
        Synchronizes an activity's cost_total with the FinancialLedger.
        Creates balanced double-entry records.
        
        [Protocol XV] Financial Transparency - All adjustments are logged.
        [AGRI-GUARDIAN] Wrapped in transaction.atomic for double-entry atomicity.
        """
        from smart_agri.core.models.finance import FinancialLedger
        
        default_currency = getattr(settings, 'DEFAULT_CURRENCY', 'YER')
        currency = getattr(activity.crop_plan, 'currency', default_currency) if activity.crop_plan_id else default_currency
        
        crop_plan = getattr(activity, 'crop_plan', None)
        common_kwargs = dict(
            activity=activity,
            created_by=user,
            currency=currency,
            farm=getattr(activity, 'farm', None) or (crop_plan.farm if crop_plan else None),
            crop_plan=crop_plan,
            cost_center=getattr(activity, 'cost_center', None),
        )

        # 1. Component targets
        components = [
            (activity.cost_materials or Decimal("0"), FinancialLedger.ACCOUNT_MATERIAL, "مواد"),
            (activity.cost_labor or Decimal("0"), FinancialLedger.ACCOUNT_LABOR, "عمالة"),
            (activity.cost_machinery or Decimal("0"), FinancialLedger.ACCOUNT_MACHINERY, "معدات"),
            (activity.cost_overhead or Decimal("0"), FinancialLedger.ACCOUNT_OVERHEAD, "محملة"),
        ]
        
        for target_cost, acct_code, label in components:
            current_balance = FinancialLedger.objects.filter(
                activity=activity, 
                account_code=acct_code
            ).aggregate(
                balance=models.Sum(models.F('debit') - models.F('credit'))
            )['balance'] or Decimal("0")
            
            delta = target_cost - current_balance
            
            if delta == 0:
                continue
                
            logger.info(f"LEDGER_SYNC: Activity {activity.pk} [{label}] | Bal: {current_balance} | Tgt: {target_cost} | Delta: {delta}")
            
            if delta > 0:
                FinancialLedger.objects.create(
                    account_code=acct_code, 
                    debit=delta, credit=0,
                    description=f"تكلفة نشاط ({label}): {activity.pk} (+{delta})",
                    **common_kwargs
                )
                FinancialLedger.objects.create(
                    account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
                    debit=0, credit=delta,
                    description=f"التزام نشاط ({label}): {activity.pk}",
                    **common_kwargs
                )
            else:
                reversal_amount = abs(delta)
                FinancialLedger.objects.create(
                    account_code=acct_code, 
                    debit=0, credit=reversal_amount,
                    description=f"قيد عكسي لتكلفة نشاط ({label}): {activity.pk} (-{reversal_amount})",
                    **common_kwargs
                )
                FinancialLedger.objects.create(
                    account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
                    debit=reversal_amount, credit=0,
                    description=f"عكس التزام نشاط ({label}): {activity.pk}",
                    **common_kwargs
                )

    @staticmethod
    @transaction.atomic
    def reverse_activity_ledger(activity, user):
        """
        Creates reversal entries for an activity being deleted.
        Ensures financial integrity during soft-delete operations.
        [AGRI-GUARDIAN] Wrapped in transaction.atomic for double-entry atomicity.
        """
        from smart_agri.core.models.finance import FinancialLedger
        
        if not activity.cost_total or activity.cost_total <= 0:
            return
        
        default_currency = getattr(settings, 'DEFAULT_CURRENCY', 'YER')
        currency = getattr(activity.crop_plan, 'currency', default_currency) if activity.crop_plan_id else default_currency
        
        cost = activity.cost_total
        
        crop_plan = getattr(activity, 'crop_plan', None)
        common_kwargs = dict(
            activity=activity,
            created_by=user,
            currency=currency,
            farm=getattr(activity, 'farm', None) or (crop_plan.farm if crop_plan else None),
            crop_plan=crop_plan,
            cost_center=getattr(activity, 'cost_center', None),
        )
        
        # Reversal entries
        components = [
            (activity.cost_materials or Decimal("0"), FinancialLedger.ACCOUNT_MATERIAL, "مواد"),
            (activity.cost_labor or Decimal("0"), FinancialLedger.ACCOUNT_LABOR, "عمالة"),
            (activity.cost_machinery or Decimal("0"), FinancialLedger.ACCOUNT_MACHINERY, "معدات"),
            (activity.cost_overhead or Decimal("0"), FinancialLedger.ACCOUNT_OVERHEAD, "محملة"),
        ]
        
        for cost_val, acct_code, label in components:
            if cost_val <= 0:
                continue
                
            FinancialLedger.objects.create(
                account_code=acct_code,
                debit=0,
                credit=cost_val,
                description=f"قيد عكسي لإلغاء نشاط ({label}): {activity.pk}",
                **common_kwargs
            )
            FinancialLedger.objects.create(
                account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
                debit=cost_val,
                credit=0,
                description=f"تصفية التزام لإلغاء نشاط ({label}): {activity.pk}",
                **common_kwargs
            )
        
        logger.info(f"LEDGER_REVERSAL: Activity {activity.pk} | Amount: {cost}")

    @staticmethod
    def sync_pending_ledger_entries(farm_id: int):
        """
        Robust Sync for Flaky Internet (Yemen-Ready).
        Uses 'Check-Then-Send' pattern per batch.
        """
        # [Agri-Guardian] Safe Imports
        import requests
        import hashlib
        from django.db import transaction
        from django.utils import timezone
        
        # Avoid circular import at top level if possible, or use local
        from smart_agri.core.models.finance import FinancialLedger
        
        HUB_URL = getattr(settings, 'FEDERATION_HUB_URL', 'http://localhost:8000')

        pending_entries = FinancialLedger.objects.filter(
            farm_id=farm_id, 
            is_synced=False
        ).order_by('created_at')[:50] # Small batches are safer

        if not pending_entries:
            return

        payload = []
        for entry in pending_entries:
            # Safe debit/credit access
            amt = entry.debit if entry.debit > 0 else entry.credit
            payload.append({
                "uuid": str(entry.id), # Vital for Idempotency
                "hash": getattr(entry, 'row_hash', ''),
                "amount": str(amt),
                # ... other fields ...
            })

        try:
            # Send batch with idempotency key based on the batch hash
            batch_hash_str = str([p['uuid'] for p in payload])
            batch_id = hashlib.md5(batch_hash_str.encode()).hexdigest()
            
            response = requests.post(
                f"{HUB_URL}/sync/ledger", 
                json={"batch_id": batch_id, "entries": payload},
                headers={"X-Idempotency-Key": batch_id}, # Network Shield
                timeout=45
            )
            
            if response.status_code in [200, 201, 409]: # 409 means 'already exists', which is effectively success
                # Mark as synced locally
                with transaction.atomic():
                    for entry in pending_entries:
                        entry.is_synced = True
                        entry.synced_at = timezone.now()
                        entry.save(update_fields=['is_synced', 'synced_at'])
            else:
                 logger.error(f"Sync failed with status {response.status_code}: {response.text}")
                        
        except requests.exceptions.RequestException as e:
            logger.warning(f"Sync failed due to network: {e}. Will retry later without data corruption.")
