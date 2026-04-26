from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from smart_agri.core.models import Asset
from smart_agri.core.services.audit_event_factory import AuditEventFactory
from smart_agri.finance.models import FinancialLedger
from smart_agri.finance.services.core_finance import FinanceService
from smart_agri.finance.services.farm_finance_authority_service import FarmFinanceAuthorityService


class FixedAssetLifecycleService:
    """Service-layer lifecycle operations for fixed assets."""

    @staticmethod
    def _assert_reason(reason: str) -> str:
        reason = (reason or "").strip()
        if not reason:
            raise ValueError("سبب العملية إلزامي للأصول الثابتة.")
        return reason

    @staticmethod
    @transaction.atomic
    def capitalize_asset(*, user, asset_id: int, capitalized_value: Decimal, effective_date=None, funding_account: str | None = None, reason: str = "", ref_id: str = "") -> dict:
        reason = FixedAssetLifecycleService._assert_reason(reason)
        effective_date = effective_date or timezone.localdate()
        asset = Asset.objects.select_for_update().select_related('farm').get(pk=asset_id, deleted_at__isnull=True)

        # Fiscal lock
        FinanceService.check_fiscal_period(effective_date, asset.farm)
        FarmFinanceAuthorityService.require_profiled_posting_authority(user=user, farm=asset.farm, action_label='رسملة أصل ثابت')

        amount = Decimal(str(capitalized_value or 0)).quantize(Decimal('0.01'))
        if amount <= 0:
            raise ValueError("قيمة الرسملة يجب أن تكون أكبر من صفر.")

        # Defaults
        debit_acct = getattr(FinancialLedger, 'ACCOUNT_FIXED_ASSET', '1600-FIXED-ASSET')
        credit_acct = funding_account or FinancialLedger.ACCOUNT_CASH_ON_HAND

        ct = ContentType.objects.get_for_model(asset.__class__)
        common = dict(
            farm=asset.farm,
            content_type=ct,
            object_id=str(asset.pk),
            created_by=user,
            description=f"رسملة أصل: {asset.name}" + (f" | مرجع: {ref_id}" if ref_id else ""),
        )

        FinancialLedger.objects.create(account_code=debit_acct, debit=amount, credit=Decimal('0.00'), **common)
        FinancialLedger.objects.create(account_code=credit_acct, debit=Decimal('0.00'), credit=amount, **common)

        event = AuditEventFactory.build(
            actor=user,
            action='FIXED_ASSET_CAPITALIZE',
            model_name='Asset',
            object_id=asset.pk,
            reason=reason,
            farm_id=asset.farm_id,
            source='fixed_asset_lifecycle',
            category='fixed_assets',
            old_value={'purchase_value': str(asset.purchase_value), 'accumulated_depreciation': str(asset.accumulated_depreciation)},
            new_value={'capitalized_value': str(amount), 'funding_account': credit_acct, 'effective_date': str(effective_date), 'ref_id': ref_id},
        )
        AuditEventFactory.record(event)

        return {'status': 'posted', 'asset_id': asset.pk, 'amount': str(amount), 'debit_account': debit_acct, 'credit_account': credit_acct}

    @staticmethod
    @transaction.atomic
    def dispose_asset(*, user, asset_id: int, proceeds_value: Decimal, effective_date=None, proceeds_account: str | None = None, reason: str = "", ref_id: str = "") -> dict:
        reason = FixedAssetLifecycleService._assert_reason(reason)
        effective_date = effective_date or timezone.localdate()
        asset = Asset.objects.select_for_update().select_related('farm').get(pk=asset_id, deleted_at__isnull=True)

        FinanceService.check_fiscal_period(effective_date, asset.farm)
        FarmFinanceAuthorityService.require_profiled_posting_authority(user=user, farm=asset.farm, action_label='استبعاد أصل ثابت')

        proceeds = Decimal(str(proceeds_value or 0)).quantize(Decimal('0.01'))
        cost = Decimal(str(asset.purchase_value or 0)).quantize(Decimal('0.01'))
        accum = Decimal(str(asset.accumulated_depreciation or 0)).quantize(Decimal('0.01'))
        nbv = (cost - accum).quantize(Decimal('0.01'))

        fixed_acct = getattr(FinancialLedger, 'ACCOUNT_FIXED_ASSET', '1600-FIXED-ASSET')
        disposal_gain_acct = getattr(FinancialLedger, 'ACCOUNT_ASSET_DISPOSAL_GAIN', '7201-ASSET-GAIN')
        disposal_loss_acct = getattr(FinancialLedger, 'ACCOUNT_ASSET_DISPOSAL_LOSS', '7202-ASSET-LOSS')
        cash_acct = proceeds_account or FinancialLedger.ACCOUNT_CASH_ON_HAND

        ct = ContentType.objects.get_for_model(asset.__class__)
        common = dict(
            farm=asset.farm,
            content_type=ct,
            object_id=str(asset.pk),
            created_by=user,
            description=f"استبعاد أصل: {asset.name}" + (f" | مرجع: {ref_id}" if ref_id else ""),
        )

        # 1) Bring accumulated depreciation to debit (reduce contra)
        if accum > 0:
            FinancialLedger.objects.create(account_code=FinancialLedger.ACCOUNT_ACCUM_DEPRECIATION, debit=accum, credit=Decimal('0.00'), **common)

        # 2) Credit fixed asset at cost
        FinancialLedger.objects.create(account_code=fixed_acct, debit=Decimal('0.00'), credit=cost, **common)

        # 3) Record proceeds
        if proceeds > 0:
            FinancialLedger.objects.create(account_code=cash_acct, debit=proceeds, credit=Decimal('0.00'), **common)

        # 4) Gain/Loss balancing
        balance = (accum + proceeds) - cost  # positive => gain, negative => loss
        if balance > 0:
            FinancialLedger.objects.create(account_code=disposal_gain_acct, debit=Decimal('0.00'), credit=balance, **common)
        elif balance < 0:
            FinancialLedger.objects.create(account_code=disposal_loss_acct, debit=abs(balance), credit=Decimal('0.00'), **common)

        event = AuditEventFactory.build(
            actor=user,
            action='FIXED_ASSET_DISPOSE',
            model_name='Asset',
            object_id=asset.pk,
            reason=reason,
            farm_id=asset.farm_id,
            source='fixed_asset_lifecycle',
            category='fixed_assets',
            old_value={'purchase_value': str(cost), 'accumulated_depreciation': str(accum), 'nbv': str(nbv)},
            new_value={'proceeds': str(proceeds), 'balance': str(balance), 'effective_date': str(effective_date), 'ref_id': ref_id},
        )
        AuditEventFactory.record(event)

        return {'status': 'posted', 'asset_id': asset.pk, 'cost': str(cost), 'accumulated_depreciation': str(accum), 'nbv': str(nbv), 'proceeds': str(proceeds), 'balance': str(balance)}
