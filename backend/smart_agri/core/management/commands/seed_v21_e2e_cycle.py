import logging
import sys
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.models.crop import Crop, CropPlan
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.log import DailyLog, AuditLog
from smart_agri.finance.models_supplier_settlement import SupplierSettlement
from smart_agri.finance.services.supplier_settlement_service import SupplierSettlementService
from smart_agri.finance.services.approval_service import ApprovalGovernanceService
from smart_agri.finance.models import ApprovalRequest, ApprovalRule
from smart_agri.inventory.models import PurchaseOrder

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run the full E2E V21 Cycle Simulation with persistent data seeding and governance checks."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting V21 Full E2E Cycle Seeding & Validation..."))

        try:
            with transaction.atomic():
                self.run_cycle()
            self.stdout.write(self.style.SUCCESS("V21 E2E Cycle Completed Successfully!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Simulation failed: {e}"))
            raise e

    def run_cycle(self):
        # 1. Provide Initial Data (Users & Roles)
        password = "Password123!"

        sysadmin, _ = User.objects.get_or_create(username="v21_sysadmin")
        sysadmin.set_password(password)
        sysadmin.is_superuser = True
        sysadmin.is_staff = True
        sysadmin.save()

        field_op, _ = User.objects.get_or_create(username="v21_field_op")
        field_op.set_password(password)
        field_op.save()

        farm_mgr, _ = User.objects.get_or_create(username="v21_farm_mgr")
        farm_mgr.set_password(password)
        farm_mgr.save()

        finance_mgr, _ = User.objects.get_or_create(username="v21_finance_mgr")
        finance_mgr.set_password(password)
        finance_mgr.save()

        self.stdout.write(self.style.SUCCESS("1. Users created successfully."))

        # Create Farms
        farm_simple, _ = Farm.objects.get_or_create(name="E2E Simple Farm", slug="e2e-simple", defaults={"tier": "SMALL"})
        fs_simple, _ = FarmSettings.objects.get_or_create(farm=farm_simple)
        fs_simple.mode = FarmSettings.MODE_SIMPLE
        fs_simple.save()
        
        farm_strict, _ = Farm.objects.get_or_create(name="E2E Strict Farm", slug="e2e-strict", defaults={"tier": "LARGE"})
        fs_strict, _ = FarmSettings.objects.get_or_create(farm=farm_strict)
        fs_strict.mode = FarmSettings.MODE_STRICT
        fs_strict.save()

        self.stdout.write(self.style.SUCCESS("2. Farms created and mode boundaries set."))

        # Assign Memberships
        FarmMembership.objects.get_or_create(user=field_op, farm=farm_simple, role="مشرف ميداني")
        FarmMembership.objects.get_or_create(user=farm_mgr, farm=farm_simple, role="مدير المزرعة")
        FarmMembership.objects.get_or_create(user=farm_mgr, farm=farm_strict, role="مدير المزرعة")
        FarmMembership.objects.get_or_create(user=finance_mgr, farm=farm_strict, role="المدير المالي للمزرعة")

        # Create Crops & Smart Card integrations
        crop, _ = Crop.objects.get_or_create(farm=farm_simple, name="E2E Tomato", crop_type="VEGETABLE")
        plan, _ = CropPlan.objects.get_or_create(
            farm=farm_simple,
            crop=crop,
            name="Q1 Smart Card Plan"
        )
        plan.smart_card_stack = {
            "base_cards": ["IRRIGATION", "FERTILIZATION"],
            "active_card": "IRRIGATION",
            "completed": False
        }
        plan.save()

        self.stdout.write(self.style.SUCCESS("3. Crops and Smart Card Stack integrated."))

        # A. Field Operator logs daily data to the smart card
        activity, _ = Activity.objects.get_or_create(
            farm=farm_simple,
            name="Morning Irrigation",
            crop_plan=plan,
            defaults={
                "activity_type": Activity.TYPE_AGRICULTURAL,
                "status": Activity.STATUS_COMPLETED,
                "requires_daily_log": True
            }
        )

        dlog = DailyLog.objects.create(
            farm=farm_simple,
            activity=activity,
            weather_conditions="Sunny",
            notes="Smart Card: IRRIGATION task executed successfully",
            created_by=field_op
        )
        self.stdout.write(self.style.SUCCESS(f"4. DailyLog execution bound to Smart Card: {dlog.activity.crop_plan.smart_card_stack['active_card']}."))

        # FINANCIAL STRICT CYCLE --
        ApprovalRule.objects.get_or_create(
            farm=farm_strict,
            module=ApprovalRule.MODULE_FINANCE,
            action="supplier_settlement",
            defaults={
                "min_amount": Decimal('0.0000'),
                "max_amount": Decimal('10000.0000'),
                "required_role": "المدير المالي للمزرعة"
            }
        )

        po = PurchaseOrder.objects.create(
            farm=farm_strict,
            vendor_name="E2E AgriSupplies Co",
            total_amount=Decimal('5000.0000'),
            status=PurchaseOrder.Status.RECEIVED
        )

        settlement = SupplierSettlementService.create_draft(
            user=farm_mgr,
            purchase_order_id=po.id,
            invoice_reference=f"INV-E2E-{po.id}"
        )

        settlement = SupplierSettlementService.submit_review(settlement.id, farm_mgr)

        req = ApprovalGovernanceService.create_request(
            user=farm_mgr,
            farm=farm_strict,
            module=ApprovalRule.MODULE_FINANCE,
            action="supplier_settlement",
            record_id=str(settlement.id),
            requested_amount=settlement.payable_amount
        )

        # Maker-Checker Blockage
        try:
            from rest_framework.exceptions import PermissionDenied
            ApprovalGovernanceService.approve_request(user=farm_mgr, request_id=req.id)
            raise Exception("CRITICAL FAILURE: Maker-Checker protocol breached!")
        except Exception as e:
            if "لا يجوز لمنشئ الطلب" in str(e):
                self.stdout.write(self.style.SUCCESS("5. Maker-Checker explicitly blocked self-approval validation. Governance healthy."))
            else:
                raise e

        # Finance Manager Approves
        ApprovalGovernanceService.approve_request(user=finance_mgr, request_id=req.id)
        
        # Finance Manager Finalizes
        settlement = SupplierSettlementService.approve(settlement.id, finance_mgr)
        self.stdout.write(self.style.SUCCESS("6. Strict Financial Supplier Settlement Approved by Finance Manager via Valid Authority."))

        self.stdout.write(self.style.WARNING("========================================"))
        self.stdout.write(self.style.WARNING("E2E DATA PROVISIONING COMPLETED."))
        self.stdout.write(self.style.WARNING("========================================"))
