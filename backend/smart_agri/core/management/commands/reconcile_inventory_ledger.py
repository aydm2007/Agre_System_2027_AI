"""
[AGRI-GUARDIAN §9.I] Reconcile Inventory Ledger
================================================
Diagnoses and optionally fixes triple-match variances by creating 
proper StockMovement + FinancialLedger entries for unreconciled inventory.

Usage:
    python manage.py reconcile_inventory_ledger                    # Dry-run
    python manage.py reconcile_inventory_ledger --fix              # Apply fixes
    python manage.py reconcile_inventory_ledger --farm "Golden Farm" --fix
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from smart_agri.core.models import Farm
from smart_agri.inventory.models import ItemInventory, StockMovement
from smart_agri.finance.models import FinancialLedger


from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = '[AGRI-GUARDIAN §9.I] Reconcile inventory triple-match variances'
    
    # ... (rest of class) ...

    @transaction.atomic
    def _create_opening_balance_movement(self, farm, inv, gap):
        """
        Create a reconciliation StockMovement entry for the gap.
        Per §9.I: Discrepancies require a "Reconciliation Adjustment" transaction.
        """
        movement = StockMovement.objects.create(
            farm=farm,
            item=inv.item,
            location=inv.location,
            qty_delta=gap,
            ref_type='reconciliation',
            ref_id=f'AG-RECON-{farm.pk}-{inv.item_id}-{date.today().isoformat()}',
            note=f'[§9.I] تسوية رصيد افتتاحي — مصالحة المطابقة الثلاثية. الفجوة: {gap:+.2f}',
        )

        # Get ContentType for StockMovement to link Ledger entries
        movement_ct = ContentType.objects.get_for_model(StockMovement)

        # Also create the corresponding Financial Ledger entries (double-entry)
        # Opening balance = Debit Inventory Asset, Credit Suspense (Opening Equity)
        abs_gap = abs(gap)
        if gap > 0:
            # Positive gap: inventory has more than movements tracked
            FinancialLedger.objects.create(
                farm=farm,
                content_type=movement_ct,
                object_id=str(movement.pk),
                account_code='1300-INV-ASSET',
                description=f'[§9.I] تسوية رصيد افتتاحي: {inv.item.name}',
                debit=abs_gap,
                credit=Decimal('0'),
                exchange_rate_at_moment=Decimal('1.0000'),
            )
            FinancialLedger.objects.create(
                farm=farm,
                content_type=movement_ct,
                object_id=str(movement.pk),
                account_code='9999-SUSPENSE',
                description=f'[§9.I] مقابل تسوية رصيد افتتاحي: {inv.item.name}',
                debit=Decimal('0'),
                credit=abs_gap,
                exchange_rate_at_moment=Decimal('1.0000'),
            )
        else:
            # Negative gap: movements show more than inventory has
            FinancialLedger.objects.create(
                farm=farm,
                content_type=movement_ct,
                object_id=str(movement.pk),
                account_code='9999-SUSPENSE',
                description=f'[§9.I] تسوية عكسية: {inv.item.name}',
                debit=abs_gap,
                credit=Decimal('0'),
                exchange_rate_at_moment=Decimal('1.0000'),
            )
            FinancialLedger.objects.create(
                farm=farm,
                content_type=movement_ct,
                object_id=str(movement.pk),
                account_code='1300-INV-ASSET',
                description=f'[§9.I] تسوية عكسية: {inv.item.name}',
                debit=Decimal('0'),
                credit=abs_gap,
                exchange_rate_at_moment=Decimal('1.0000'),
            )

        self.stdout.write(self.style.SUCCESS(
            f'    ✅ Created reconciliation: Movement + Ledger entry for gap {gap:+.2f}'
        ))
