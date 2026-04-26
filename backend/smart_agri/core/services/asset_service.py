from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from smart_agri.core.models import Asset
from smart_agri.finance.models import FinancialLedger
import logging

logger = logging.getLogger(__name__)

class AssetService:
    """
    Asset Management Service (IAS 16).
    Handles Depreciation & Lifecycle.
    """
    
    @staticmethod
    @transaction.atomic
    def run_monthly_depreciation(user):
        """
        Runs monthly depreciation for all active assets.
        Ideally called by a Celery Beat job on the 1st of every month.
        """
        today = timezone.now().date()
        processed_count = 0
        
        # Select active assets that are not fully depreciated
        # Condition: (Purchase Value - Accumulated) > Salvage Value
        
        assets = Asset.objects.filter(
            status='active', 
            deleted_at__isnull=True
        ).select_for_update()
        
        assets_to_update = []
        ledger_entries = []
        
        for asset in assets:
            if asset.useful_life_years <= 0:
                continue
                
            book_value = asset.purchase_value - asset.accumulated_depreciation
            max_depreciable = asset.purchase_value - asset.salvage_value
            
            if asset.accumulated_depreciation >= max_depreciable:
                continue # Fully depreciated
            
            monthly_depreciation = Decimal(0)
            
            if asset.depreciation_method == Asset.METHOD_STRAIGHT_LINE:
                total_months = Decimal(asset.useful_life_years * 12)
                # Standard division to avoid precision context issues in transactions
                monthly_depreciation = ((asset.purchase_value - asset.salvage_value) / total_months).quantize(Decimal("0.0001")) # agri-guardian: decimal-safe
                
            elif asset.depreciation_method == Asset.METHOD_DECLINING:
                 # Simplified Double Declining for now
                 # Rate = (2 / Life Years) / 12 * Book Value
                 rate_annual = (Decimal(2) / Decimal(asset.useful_life_years)).quantize(Decimal("0.000001")) # agri-guardian: decimal-safe
                 monthly_depreciation = ((book_value * rate_annual) / Decimal(12)).quantize(Decimal("0.0001")) # agri-guardian: decimal-safe
            else:
                 monthly_depreciation = Decimal(0)
                 
            if monthly_depreciation <= 0:
                 continue
                 
            # Cap at remaining value
            remaining_to_depreciate = max_depreciable - asset.accumulated_depreciation
            if monthly_depreciation > remaining_to_depreciate:
                monthly_depreciation = remaining_to_depreciate
                
            # Update Asset
            asset.accumulated_depreciation += monthly_depreciation
            assets_to_update.append(asset)
            
            # GL Entry
            asset_currency = getattr(asset, "currency", None) or getattr(settings, "DEFAULT_CURRENCY", "YER")
            ledger_entries.append(
                FinancialLedger(
                    account_code=FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
                    debit=monthly_depreciation,
                    credit=0,
                    description=f"مصروف استهلاك: {asset.name} ({today.strftime('%Y-%m')})",
                    created_by=user, # System User
                    currency=asset_currency,
                    farm=asset.farm,
                    cost_center=getattr(asset, 'cost_center', None),
                )
            )
            ledger_entries.append(
                FinancialLedger(
                    account_code=FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION,
                    debit=0,
                    credit=monthly_depreciation,
                    description=f"مجمع استهلاك: {asset.name} ({today.strftime('%Y-%m')})",
                    created_by=user,
                    currency=asset_currency,
                    farm=asset.farm,
                    cost_center=getattr(asset, 'cost_center', None),
                )
            )
            processed_count += 1
            
        if assets_to_update:
            Asset.objects.bulk_update(assets_to_update, ['accumulated_depreciation'])
        if ledger_entries:
            FinancialLedger.objects.bulk_create(ledger_entries)
            
        logger.info(f"Depreciation Run Complete: Processed {processed_count} assets.")
        return processed_count
    @staticmethod
    def calculate_operational_solar_depreciation(asset: Asset, hours: Decimal) -> Decimal:
        """
        Operational depreciation for Solar assets (hour-based reserve accrual).
        """
        # [Axis 15] Dual-Mode ERP (Flexible Toggle)
        try:
            from smart_agri.core.models.settings import FarmSettings
            farm_settings = FarmSettings.objects.filter(farm=asset.farm).first()
            if farm_settings and not farm_settings.enable_depreciation:
                return Decimal("0.0000")
        except (ImportError, ObjectDoesNotExist, AttributeError, TypeError):
            pass

        if not asset or asset.category != "Solar":
            return Decimal("0.0000")
        if asset.useful_life_years <= 0:
            return Decimal("0.0000")

        hours_dec = Decimal(str(hours or 0))
        if hours_dec <= 0:
            return Decimal("0.0000")

        depreciable_base = Decimal(str(asset.purchase_value or 0)) - Decimal(str(asset.salvage_value or 0))
        if depreciable_base <= 0:
            return Decimal("0.0000")

        # Solar assets are treated as continuously available (24h/day) for reserve accrual.
        useful_life_hours = Decimal(asset.useful_life_years) * Decimal("365") * Decimal("24")
        if useful_life_hours <= 0:
            return Decimal("0.0000")

        hourly_rate = (depreciable_base / useful_life_hours).quantize(Decimal("0.000001")) # agri-guardian: decimal-safe
        return (hours_dec * hourly_rate).quantize(Decimal("0.0001"))

    @staticmethod
    @transaction.atomic
    def post_solar_operational_depreciation(asset: Asset, hours: Decimal, user) -> Decimal:
        """
        [AGRI-GUARDIAN §Axis-9] Auto-post solar operational depreciation to the
        Financial Ledger.

        Creates double-entry GL lines:
          Dr  7000-DEP-EXP  (Depreciation Expense)
          Cr  1500-ACC-DEP  (Accumulated Depreciation)

        Also updates the asset's accumulated_depreciation field.

        Returns the depreciation amount posted (Decimal), or 0 if nothing posted.
        """
        amount = AssetService.calculate_operational_solar_depreciation(asset, hours)
        if amount <= 0:
            return Decimal("0.0000")

        # Cap at remaining depreciable amount
        max_depreciable = Decimal(str(asset.purchase_value or 0)) - Decimal(str(asset.salvage_value or 0))
        remaining = max_depreciable - Decimal(str(asset.accumulated_depreciation or 0))
        if remaining <= 0:
            return Decimal("0.0000")
        if amount > remaining:
            amount = remaining

        # Lock asset row for atomic update
        locked_asset = Asset.objects.select_for_update().get(pk=asset.pk)
        locked_asset.accumulated_depreciation = (
            Decimal(str(locked_asset.accumulated_depreciation or 0)) + amount
        )
        locked_asset.save(update_fields=['accumulated_depreciation'])

        asset_currency = getattr(asset, 'currency', None) or getattr(settings, 'DEFAULT_CURRENCY', 'YER')
        today_str = timezone.now().date().strftime('%Y-%m-%d')

        # Dr Depreciation Expense
        FinancialLedger.objects.create(
            account_code=FinancialLedger.ACCOUNT_DEPRECIATION_EXPENSE,
            debit=amount,
            credit=0,
            description=f"استهلاك تشغيلي للأصول الشمسية: {asset.name} ({today_str}, {hours}h)",
            created_by=user,
            currency=asset_currency,
            farm=asset.farm,
            cost_center=getattr(asset, 'cost_center', None),
        )
        # Cr Accumulated Depreciation
        FinancialLedger.objects.create(
            account_code=FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION,
            debit=0,
            credit=amount,
            description=f"تجنيب احتياطي الأصول الشمسية: {asset.name} ({today_str}, {hours}h)",
            created_by=user,
            currency=asset_currency,
            farm=asset.farm,
            cost_center=getattr(asset, 'cost_center', None),
        )

        logger.info(
            f"SOLAR_DEPRECIATION_POSTED: asset={asset.id}, hours={hours}, amount={amount}"
        )
        return amount
