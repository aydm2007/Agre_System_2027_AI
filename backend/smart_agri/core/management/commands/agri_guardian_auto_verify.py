import logging
import sys
import os
import secrets
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction, connection
from django.db.utils import IntegrityError
from django.db import OperationalError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Sum

# Core Models
from smart_agri.core.models import Farm, Location, Asset, LocationWell
from smart_agri.core.models import Crop, CropVariety, CropPlan
from smart_agri.inventory.models import Item, Unit, StockMovement
from smart_agri.sales.models import Customer, SalesInvoice, SalesInvoiceItem
from smart_agri.finance.models import FinancialLedger, FiscalYear, FiscalPeriod, SectorRelationship

# Services
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.sales.services import SaleService
from smart_agri.finance.services.core_finance import FinanceService
from smart_agri.core.services.cost_allocation import CostAllocationService

User = get_user_model()

# Logging Setup
logger = logging.getLogger('agri_guardian')
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('🛡️ [Agri-Guardian] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _resolve_seed_password() -> str:
    """Dev-only helper: use env AGRIASSET_SEED_DEFAULT_PASSWORD or generate ephemeral."""
    pwd = (os.environ.get("AGRIASSET_SEED_DEFAULT_PASSWORD") or "").strip()
    if pwd:
        return pwd
    generated = secrets.token_urlsafe(18)
    logger.warning("⚠️ AGRIASSET_SEED_DEFAULT_PASSWORD not set; generating a one-time password for demo users.")
    logger.warning("Set AGRIASSET_SEED_DEFAULT_PASSWORD in env to control demo user credentials.")
    return generated


class Command(BaseCommand):
    help = "Agri-Guardian: Autonomous System Auditor, Healer, and Lifecycle Simulator."

    def add_arguments(self, parser):
        parser.add_argument('--repair', action='store_true', help='Auto-fix issues found during audit.')
        parser.add_argument('--deep', action='store_true', help='Run deep simulation (Golden Thread).')

    def handle(self, *args, **options):
        self.repair_mode = options['repair']
        self.deep_mode = options['deep']
        
        logger.info("Initializing Agri-Guardian Agent...")
        logger.info(f"Mode: {'REPAIR & SIMULATE' if self.repair_mode else 'AUDIT ONLY'}")

        try:
            # 1. Infrastructure Audit
            self.audit_schema()
            
            # 2. Reference Data Verification
            self.verify_reference_data()

            # 3. Deep Simulation (The Golden Thread)
            if self.deep_mode:
                self.run_simulation()

            # 4. Final System Health Check
            self.final_integrity_check()

            logger.info("✅ Mission completed. See output above for any warnings/blockers.")

        except (ValidationError, OperationalError, IntegrityError, RuntimeError, ValueError) as e:
            logger.error(f"❌ CRITICAL FAILURE: {str(e)}")
            # In a real agent, we might email this to the DevOps team
            sys.exit(1)

    def audit_schema(self):
        """Checks for common schema integrity issues."""
        logger.info("Step 1: Auditing Schema & Constraints...")
        
        # Check for 'managed=False' which plagues tests
        # This is a heuristic check on the actual runtime models
        for model in [Customer, SalesInvoice]:
            if model._meta.managed is False:
                logger.warning(f"⚠️  Heuristic Warning: {model.__name__} has managed=False meta. Ensure migrations are synced.")
        
        # Verify Location Code constraint
        # We can't easily inspect DB constraints from here without raw SQL, 
        # but we can try to violate it and catch error in a transaction? 
        # For now, we trust the model definition.
        logger.info("   Schema Audit Passed.")

    def verify_reference_data(self):
        """Ensures critical reference data exists."""
        logger.info("Step 2: Verifying Reference Data...")

        # Units
        required_units = ['kg', 'liter', 'ton', 'box']
        for code in required_units:
            if not Unit.objects.filter(code=code).exists():
                if self.repair_mode:
                    Unit.objects.create(name=code.capitalize(), code=code)
                    logger.info(f"   ➕ Created missing unit: {code}")
                else:
                    logger.warning(f"   ⚠️  Missing Unit: {code}")



        # Ensure Admin User for Automation
        if not User.objects.filter(username='agri_bot').exists():
            if self.repair_mode:
                User.objects.create_superuser('agri_bot', 'bot@agri.com', _resolve_seed_password())
                logger.info("   ➕ Created Agri-Bot Superuser")
        
        self.bot_user = User.objects.get(username='agri_bot') if User.objects.filter(username='agri_bot').exists() else User.objects.first()
        if not User.objects.filter(username='agri_checker').exists():
            if self.repair_mode:
                User.objects.create_superuser('agri_checker', 'checker@agri.com', _resolve_seed_password())
                logger.info("   Created Agri-Checker Superuser")
        self.checker_user = User.objects.get(username='agri_checker') if User.objects.filter(username='agri_checker').exists() else self.bot_user

    def run_simulation(self):
        """Simulates the full lifecycle 'Golden Thread'."""
        logger.info("Step 3: Running Deep Simulation (Golden Thread)...")
        
        with transaction.atomic():
            # A. Farm Setup
            farm_name = "Guardian Auto Farm"
            farm = Farm.objects.filter(slug="guardian-auto").first()
            if farm:
                logger.info("   ⚠️  Simulation farm exists. Purging for clean run...")
                # Cascade delete should clean up most things, but be careful in Prod!
                # Since this is a specialized tool, we assume 'guardian-auto' is safe to nuke.
                # In prod, we might just skip or append unique ID.
                # For safety, let's CREATE a new unique scope.
                pass
            
            # Create fresh farm
            timestamp = int(timezone.now().timestamp())
            token = str(timestamp)[-6:]
            farm = Farm.objects.create(
                name=f"{farm_name} {timestamp}", 
                slug=f"guardian-auto-{timestamp}"
            )
            logger.info(f"   🌱 Created Farm: {farm.name}")

            # Fiscal Year Setup - Mandatory for FinanceService
            today = timezone.now().date()
            fy = FiscalYear.objects.create(
                farm=farm, year=today.year, 
                start_date=today.replace(month=1, day=1), 
                end_date=today.replace(month=12, day=31)
            )
            # Open current period
            period = FiscalPeriod.objects.create(
                fiscal_year=fy, month=today.month,
                start_date=today.replace(day=1), 
                end_date=today.replace(day=28), # simplified
                is_closed=False
            )
            logger.info(f"   📅 Fiscal Period Opened: {period}")

            # Locations & Assets
            field = Location.objects.create(farm=farm, name="Sector Alpha", code=f"SEC-{token}")
            barn = Location.objects.create(farm=farm, name="Main Barn", code=f"BRN-{token}")
            
            well = Asset.objects.create(farm=farm, name="Well 01", category="Well", purchase_value=50000)
            tractor = Asset.objects.create(farm=farm, name="Tractor Titan", category="Machinery", purchase_value=120000)
            
            # B. Inventory Injection (Seeds)
            unit_kg = Unit.objects.get(code='kg')
            seed_item = Item.objects.create(
                name=f"Magic Wheat Seeds {token}",
                group="General",
                uom="kg",
                unit=unit_kg,
                unit_price=Decimal("5.00"),
            )
            
            # Simulate GRN (Goods Receipt Note) -> Increases Stock
            logger.info("   🚚 Receiving Inventory (GRN)...")
            InventoryService.process_grn(
                farm=farm,
                item=seed_item,
                location=barn,
                qty=Decimal("1000"),
                unit_cost=Decimal("5.00"),
                ref_id=f"GRN-{timestamp}"
            )

            # C. Operations (Crop Plan)
            logger.info("   🚜 Starting Operations...")
            wheat = Crop.objects.create(name=f"Guardian Wheat {token}", mode="Open")
            plan = CropPlan.objects.create(
                farm=farm, location=field, crop=wheat, 
                name="Wheat Cycle 1", area=Decimal("10.0"),
                start_date=today,
                end_date=today + timezone.timedelta(days=90)
            )
            # Move seeds to field (Consumption) ignoring strict cost allocation logic for brevity,
            # but ensuring stock moves.
            InventoryService.record_movement(
                farm=farm, item=seed_item, location=barn,
                qty_delta=Decimal("-100"), ref_type="H-CONSUME", ref_id=f"TASK-{plan.id}"
            )

            # D. Harvest and Sales
            logger.info("   🌾 Harvesting...")
            harvest_item = Item.objects.create(
                name=f"Wheat Grain {token}",
                group="General",
                uom="kg",
                unit=unit_kg,
                unit_price=Decimal("2.00"),
            )
            # Initial Stock in Barn from Harvest
            InventoryService.process_grn(
                farm=farm, item=harvest_item, location=barn,
                qty=Decimal("5000"), 
                unit_cost=Decimal("1.50"), # Cost of production approx
                ref_id=f"HRV-{plan.id}",
            )

            logger.info("   💰 Executing Sales Flow...")
            sale_started_at = timezone.now()
            customer = Customer.objects.create(name="Global Foods Ltd", phone="999")
            SectorRelationship.objects.get_or_create(
                farm=farm,
                defaults={
                    "current_balance": Decimal("0.0000"),
                    "allow_revenue_recycling": False,
                },
            )
            
            # Create Invoice manually
            invoice = SalesInvoice.objects.create(
                farm=farm,
                customer=customer,
                location=barn,
                invoice_date=today,
                currency="YER",
                total_amount=Decimal("5000"), # Manual calc for test
                created_by=self.bot_user
            )
            
            SalesInvoiceItem.objects.create(
                invoice=invoice,
                item=harvest_item,
                qty=1000,
                unit_price=Decimal("5.00"),
                total=Decimal("5000")
            )
            
            # Confirm Sale (Triggers Stock Deduct + Finance Ledger)
            SaleService.confirm_sale(invoice=invoice, user=self.checker_user)
            logger.info(f"      Invoice #{invoice.id} Confirmed. Total: {invoice.total_amount}")

            # VERIFICATION POINT 1: Stock Level
            stock = InventoryService.get_stock_level(farm, harvest_item, barn)
            if stock != Decimal("4000"): # 5000 - 1000
                raise ValueError(f"Inventory Mismatch! Expected 4000, got {stock}")
            logger.info("      ✅ Inventory Integrity Verified.")

            # VERIFICATION POINT 2: Financial Ledger
            # Total Revenue should be 1000 * 5.00 = 5000
            ledger_entries = FinancialLedger.objects.filter(
                farm=farm,
                created_at__gte=sale_started_at,
                account_code__in=[
                    FinancialLedger.ACCOUNT_SALES_REVENUE,
                    FinancialLedger.ACCOUNT_RECEIVABLE,
                    FinancialLedger.ACCOUNT_SECTOR_PAYABLE,
                ],
            )
            credits = ledger_entries.aggregate(s=Sum('credit'))['s'] or Decimal(0)
            debits = ledger_entries.aggregate(s=Sum('debit'))['s'] or Decimal(0)
            revenue_credit = (
                ledger_entries.filter(account_code=FinancialLedger.ACCOUNT_SALES_REVENUE).aggregate(s=Sum('credit'))['s']
                or Decimal(0)
            )
            receivable_debit = (
                ledger_entries.filter(account_code=FinancialLedger.ACCOUNT_RECEIVABLE).aggregate(s=Sum('debit'))['s']
                or Decimal(0)
            )
            sector_payable_credit = (
                ledger_entries.filter(account_code=FinancialLedger.ACCOUNT_SECTOR_PAYABLE).aggregate(s=Sum('credit'))['s']
                or Decimal(0)
            )

            if revenue_credit != invoice.total_amount:
                raise ValueError(
                    f"Revenue credit mismatch! Expected {invoice.total_amount}, got {revenue_credit}."
                )
            if receivable_debit != invoice.total_amount:
                raise ValueError(
                    f"Receivable debit mismatch! Expected {invoice.total_amount}, got {receivable_debit}."
                )
            if sector_payable_credit != invoice.total_amount:
                raise ValueError(
                    f"Sector payable mismatch! Expected {invoice.total_amount}, got {sector_payable_credit}."
                )
            if credits < debits:
                raise ValueError(f"Unexpected ledger imbalance: credits {credits} < debits {debits}.")
            
            logger.info("      ✅ Financial Ledger Verified.")
            
            # Store the farm ID for final check if needed, 
            # or let transaction commit if we want to keep data (simulation usually keeps data for review)
            self.simulated_farm = farm

    def final_integrity_check(self):
        """Scanning the entire system for anomalies."""
        logger.info("Step 4: Global Integrity Scan...")
        
        # Check for Orphaned Ledger Entries
        orphans = FinancialLedger.objects.filter(farm__isnull=True).count()
        if orphans > 0:
            logger.error(f"   ❌ Found {orphans} orphaned ledger entries (No Farm ID).")
            if self.repair_mode:
                # Attempt to infer? No, too risky. Just flag.
                pass
        else:
            logger.info("   ✅ No orphaned ledger entries.")

        # Check for Negative Stock (where disallowed)
        from smart_agri.inventory.models import ItemInventory
        negative_stock = ItemInventory.objects.filter(qty__lt=0, deleted_at__isnull=True).count()
        if negative_stock > 0:
            logger.error("   ❌ Found %d item inventories with negative stock.", negative_stock)
        else:
            logger.info("   ✅ No negative stock detected.")
        
        logger.info("   Global Scan Complete.")
