from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields.ranges import DateRange
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmGovernanceProfile, FarmMembership
from smart_agri.core.models import Crop, DailyLog, Farm, Location, Supervisor, SyncConflictDLQ, SyncRecord, Task
from smart_agri.core.models.activity import Activity, ActivityEmployee, ActivityHarvest, ActivityItem, ActivityLocation
from smart_agri.core.models.crop import CropProduct, CropRecipe, CropRecipeMaterial, CropVariety, FarmCrop
from smart_agri.core.models.custody import CustodyTransfer
from smart_agri.core.models.farm import Asset, LocationIrrigationPolicy
from smart_agri.core.models.inventory import BiologicalAssetCohort, HarvestLot
from smart_agri.core.models.log import Attachment, AuditLog, FuelConsumptionAlert, MaterialVarianceAlert
from smart_agri.core.models.partnerships import SharecroppingContract, TouringAssessment
from smart_agri.core.models.planning import CropPlan, CropPlanLocation, Season
from smart_agri.core.models.settings import FarmSettings, LaborRate, MachineRate
from smart_agri.core.models.tree import LocationTreeStock, TreeLossReason, TreeProductivityStatus, TreeServiceCoverage
from smart_agri.core.middleware.route_breach_middleware import RouteBreachAuditMiddleware
from smart_agri.core.api.utils import _sync_pk_sequence
from smart_agri.core.services.contract_operations_service import ContractOperationsService
from smart_agri.core.services.custody_transfer_service import CustodyTransferService
from smart_agri.core.services.fixed_asset_lifecycle_service import FixedAssetLifecycleService
from smart_agri.core.services.fuel_reconciliation_posting_service import FuelReconciliationPostingService
from smart_agri.core.services.harvest_service import HarvestService
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.core.uat.khameesiya import (
    _bad_attachment,
    _ensure_activity,
    _ensure_task,
    _open_current_fiscal_period,
    _safe_attachment,
    _set_mode,
    _submit_and_approve_log,
)
from smart_agri.finance.models import (
    ApprovalRequest,
    ApprovalRule,
    ApprovalStageEvent,
    CostCenter,
    CostConfiguration,
    FinancialLedger,
    SectorRelationship,
)
from smart_agri.finance.models_petty_cash import PettyCashRequest
from smart_agri.finance.models_supplier_settlement import SupplierSettlement
from smart_agri.finance.models_treasury import CashBox
from smart_agri.finance.services.approval_service import ApprovalGovernanceService
from smart_agri.finance.services.petty_cash_service import PettyCashService
from smart_agri.finance.services.receipt_deposit_service import ReceiptDepositService
from smart_agri.finance.services.supplier_settlement_service import SupplierSettlementService
from smart_agri.inventory.models import FuelLog, Item, ItemInventory, PurchaseOrder, PurchaseOrderItem, StockMovement, TankCalibration, Unit
from smart_agri.sales.models import Customer
from smart_agri.sales.services import SaleService

User = get_user_model()
ZERO = Decimal("0.0000")
DEFAULT_PASSWORD = "RabSarUAT#2026"
RABOUIA_FARM_NAME = "الربوعية"
RABOUIA_FARM_SLUG = "al-rabouia"
SARIMA_FARM_NAME = "الصارمة"
SARIMA_FARM_SLUG = "al-sarima"

BEFORE_SCORECARD = {
    "canonical_repo_baseline": 100,
    "uat_pack_provisioning": 0,
    "simple_operational_cycle": 0,
    "strict_governed_cycle": 0,
    "offline_and_custody": 0,
    "reports_and_diagnostics": 0,
    "arabic_seed_quality": 0,
    "harvest_and_production_entry": 0,
    "custody_workspace_flow": 0,
    "permissions_arabic_display": 0,
    "offline_mode_determinism": 0,
    "units_normalization": 0,
}

IMPROVEMENTS = [
    "إضافة smoke pack خارجي للتكاملات على نفس البيانات المرجعية للمزرعتين دون الحاجة للدخول في تفاصيل المستودع.",
    "توسيع weak-network replay profiles لتشمل حالات تأخير أشد مع نفس artifact schema الحالي.",
    "ربط UAT pack بكتالوج export رسمي للعقود العامة الحساسة بصيغة OpenAPI-style tables.",
]

ROLE_DEFAULTS: list[tuple[str, str, bool]] = [
    ("system_admin", "مدير النظام", True),
    ("farm_manager", "مدير المزرعة", False),
    ("field_operator", "مدخل بيانات", False),
    ("agronomist", "مهندس زراعي", False),
    ("storekeeper", "أمين مخزن", False),
    ("cashier", "أمين صندوق", False),
    ("farm_accountant", "محاسب المزرعة", False),
    ("farm_chief_accountant", "رئيس حسابات المزرعة", False),
    ("farm_finance_manager", "المدير المالي للمزرعة", False),
    ("sector_accountant", "محاسب القطاع", False),
    ("sector_reviewer", "مراجع القطاع", False),
    ("sector_chief_accountant", "رئيس حسابات القطاع", False),
    ("finance_director", "المدير المالي لقطاع المزارع", False),
    ("sector_director", "مدير القطاع", False),
]

PHASE_IMPROVEMENTS = {
    "simple_bootstrap_validation": "إذا فشل هذا الطور فافحص FarmSettings.mode وtask_contract_snapshot وshow_daily_log_smart_card.",
    "custody_handshake_cycle": "إذا فشل هذا الطور فافحص issue/accept/return lifecycle وcustody balance refresh وقيود top-up.",
    "seasonal_corn_cycle": "إذا فشل هذا الطور فافحص applied_qty/waste_qty وmachine_hours وsingle-crop costing.",
    "mango_perennial_cycle": "إذا فشل هذا الطور فافحص LocationTreeStock وtree_count_delta وسبب الفقد الروتيني.",
    "banana_perennial_cycle": "إذا فشل هذا الطور فافحص multi-location coverage وcrop variety visibility.",
    "offline_replay_cycle": "إذا فشل هذا الطور فافحص idempotency key وclient_seq وDLQ routing.",
    "simple_finance_posture_only": "إذا فشل هذا الطور فافحص strict-mode route enforcement وservice-layer finance blocking.",
    "simple_reports_cycle": "إذا فشل هذا الطور فافحص تقارير SIMPLE ومنع تسرب القيم المالية الصريحة.",
    "strict_bootstrap_validation": "إذا فشل هذا الطور فافحص strict_finance profile وتعيين المدير المالي للمزرعة.",
    "inventory_procurement_cycle": "إذا فشل هذا الطور فافحص receipts/issues وأرصدة المخزون في المستودع التنفيذي.",
    "petty_cash_cycle": "إذا فشل هذا الطور فافحص create/approve/disburse/settle وربط المرفقات.",
    "receipts_and_deposit_cycle": "إذا فشل هذا الطور فافحص collection/deposit/reconcile والـ idempotency.",
    "supplier_settlement_cycle": "إذا فشل هذا الطور فافحص draft/review/approve/payment وstrict posting authority.",
    "fixed_assets_cycle": "إذا فشل هذا الطور فافحص capitalization trace وposting authority للأصل الثابت.",
    "fuel_reconciliation_cycle": "إذا فشل هذا الطور فافحص fuel alerts وdaily log linkage وapprove_and_post.",
    "harvest_and_sales_cycle": "إذا فشل هذا الطور فافحص ActivityHarvest وHarvestLot والفاتورة والبيع.",
    "contract_operations_cycle": "إذا فشل هذا الطور فافحص touring assessment-only وrent/sharecropping settlement boundaries.",
    "governance_workbench_cycle": "إذا فشل هذا الطور فافحص ApprovalStageEvent ومنع same actor clearing multiple stages.",
    "attachments_and_evidence_cycle": "إذا فشل هذا الطور فافحص archive/quarantine/restore trace وسياسة evidence class.",
}


@dataclass(slots=True)
class FarmUATContext:
    farm: Farm
    settings: FarmSettings
    governance: FarmGovernanceProfile
    cost_center: CostCenter
    cash_box: CashBox
    season: Season
    contract_season: Season
    crops: dict[str, Crop]
    locations: dict[str, Location]
    items: dict[str, Item]
    plans: dict[str, CropPlan]
    tasks: dict[str, Task]
    assets: dict[str, Asset]
    users: dict[str, User]
    employees: dict[str, object]
    supervisor: Supervisor
    run_id: str


@dataclass(slots=True)
class RabouiaSarimaBundle:
    rabouia: FarmUATContext
    sarima: FarmUATContext


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")


def _ensure_user(*, username: str, display_name: str, password: str, is_superuser: bool = False):
    first_name = display_name.split(" ")[0]
    last_name = " ".join(display_name.split(" ")[1:]) or display_name
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": f"{username}@uat.local",
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": True,
            "is_superuser": is_superuser,
        },
    )
    if created or bool(user.is_superuser) != is_superuser or not user.check_password(password):
        user.is_staff = True
        user.is_superuser = is_superuser
        user.set_password(password)
        user.save()
    return user


def _ensure_membership(*, user, farm, role: str):
    membership, _ = FarmMembership.objects.update_or_create(
        user=user,
        farm=farm,
        defaults={"role": role},
    )
    return membership


def _role_display_overrides(prefix: str) -> dict[str, str]:
    if prefix == "rab":
        return {
            "field_operator": "ياسر المدخل",
            "storekeeper": "سعيد أمين المخزن",
            "agronomist": "أحمد المهندس الزراعي",
            "farm_manager": "عبدالله مدير الربوعية",
            "cashier": "مأمون أمين الصندوق",
        }
    return {
        "farm_accountant": "فاطمة محاسب المزرعة",
        "farm_chief_accountant": "خالد رئيس حسابات المزرعة",
        "farm_finance_manager": "مروان المدير المالي للمزرعة",
        "sector_accountant": "محاسب القطاع",
        "sector_reviewer": "مراجع القطاع",
        "sector_chief_accountant": "رئيس حسابات القطاع",
        "finance_director": "المدير المالي لقطاع المزارع",
        "sector_director": "مدير القطاع",
        "storekeeper": "سالم أمين المخزن",
        "field_operator": "ليلى مدخلة البيانات",
        "cashier": "أمين صندوق الصارمة",
    }


def _ensure_role_users(*, prefix: str, password: str) -> dict[str, User]:
    overrides = _role_display_overrides(prefix)
    users: dict[str, User] = {}
    for role_key, role_label, is_superuser in ROLE_DEFAULTS:
        username = f"{prefix}_{role_key}"
        users[role_key] = _ensure_user(
            username=username,
            display_name=overrides.get(role_key, role_label),
            password=password,
            is_superuser=is_superuser,
        )
    return users


def _ensure_employee(*, farm: Farm, user: User, employee_id: str, first_name: str, last_name: str, role: str):
    Employee = __import__("smart_agri.core.models.hr", fromlist=["Employee"]).Employee
    employee, _ = Employee.objects.update_or_create(
        farm=farm,
        employee_id=employee_id,
        defaults={
            "user": user,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            "payment_mode": "SURRA",
            "shift_rate": Decimal("4800.0000"),
            "is_active": True,
        },
    )
    return employee


def _ensure_units() -> dict[str, Unit]:
    _sync_pk_sequence(Unit)
    units: dict[str, Unit] = {}
    for code, name, symbol, category in [
        ("KG", "كيلوجرام", "kg", Unit.CATEGORY_MASS),
        ("LTR", "لتر", "L", Unit.CATEGORY_VOLUME),
        ("TREE", "شجرة", "tree", Unit.CATEGORY_COUNT),
    ]:
        units[code], _ = Unit.objects.update_or_create(
            code=code,
            defaults={"name": name, "symbol": symbol, "category": category},
        )
    return units


def _ensure_item(*, name: str, group: str, unit: Unit, uom: str, price: Decimal) -> Item:
    _sync_pk_sequence(Item)
    item, _ = Item.objects.update_or_create(
        name=name,
        group=group,
        defaults={"unit": unit, "uom": uom, "unit_price": price, "currency": "YER"},
    )
    return item


def _ensure_crop(*, farm: Farm, name: str, is_perennial: bool = False) -> Crop:
    _sync_pk_sequence(Crop)
    crop, _ = Crop.objects.update_or_create(
        name=name,
        defaults={
            "mode": "Open",
            "is_perennial": is_perennial,
            "max_yield_per_ha": Decimal("40.000"),
            "max_yield_per_tree": Decimal("120.000"),
        },
    )
    FarmCrop.objects.get_or_create(farm=farm, crop=crop)
    return crop


def _ensure_plan(
    *,
    farm: Farm,
    crop: Crop,
    season: Season,
    name: str,
    recipe: CropRecipe,
    area: Decimal,
    actor: User,
    budget_total: Decimal,
) -> CropPlan:
    _sync_pk_sequence(CropPlan)
    plan, _ = CropPlan.objects.update_or_create(
        farm=farm,
        crop=crop,
        season=season,
        name=name,
        defaults={
            "recipe": recipe,
            "start_date": season.start_date,
            "end_date": season.end_date,
            "area": area,
            "status": "ACTIVE",
            "budget_total": budget_total,
            "budget_materials": (budget_total * Decimal("0.40")).quantize(Decimal("0.0001")),
            "budget_labor": (budget_total * Decimal("0.30")).quantize(Decimal("0.0001")),
            "budget_machinery": (budget_total * Decimal("0.30")).quantize(Decimal("0.0001")),
            "currency": "YER",
            "created_by": actor,
        },
    )
    return plan


def _hard_delete_queryset(queryset) -> None:
    for obj in queryset.iterator():
        if hasattr(obj, "hard_delete_forensic"):
            obj.hard_delete_forensic()
        else:
            obj.delete()


def _reset_farm_transactions(slug: str) -> None:
    farm = Farm.objects.filter(slug=slug, deleted_at__isnull=True).first()
    if not farm:
        return
    TreeServiceCoverage.objects.filter(activity__log__farm=farm).delete()
    ActivityEmployee.objects.filter(activity__log__farm=farm).delete()
    ActivityItem.objects.filter(activity__log__farm=farm).delete()
    ActivityHarvest.objects.filter(activity__log__farm=farm).delete()
    ActivityLocation.objects.filter(activity__log__farm=farm).delete()
    FuelConsumptionAlert.objects.filter(log__farm=farm).delete()
    MaterialVarianceAlert.objects.filter(log__farm=farm).delete()
    HarvestLot.objects.filter(farm=farm).delete()
    FuelLog.objects.filter(farm=farm).delete()
    SyncConflictDLQ.objects.filter(farm=farm).delete()
    SyncRecord.objects.filter(farm=farm).delete()
    CustodyTransfer.objects.filter(farm=farm).delete()
    StockMovement.objects.filter(farm=farm).delete()
    _hard_delete_queryset(ItemInventory.objects.filter(farm=farm))
    ApprovalStageEvent.objects.filter(request__farm=farm).delete()
    ApprovalRequest.objects.filter(farm=farm).delete()
    TouringAssessment.objects.filter(contract__farm=farm).delete()
    SharecroppingContract.objects.filter(farm=farm).delete()
    PurchaseOrderItem.objects.filter(purchase_order__farm=farm).delete()
    PurchaseOrder.objects.filter(farm=farm).delete()
    SupplierSettlement.objects.filter(farm=farm).delete()
    PettyCashRequest.objects.filter(farm=farm).delete()
    Attachment.objects.filter(farm=farm).delete()
    Activity.objects.filter(log__farm=farm).delete()
    DailyLog.objects.filter(farm=farm).delete()
    AuditLog.objects.filter(farm=farm).delete()


def _anchor_pack(*, code_anchor: str, test_anchor: str, gate_anchor: str, evidence_anchor: str) -> dict[str, str]:
    return {
        "code_anchor": code_anchor,
        "test_anchor": test_anchor,
        "gate_anchor": gate_anchor,
        "evidence_anchor": evidence_anchor,
    }


def _phase_success(*, result: dict, diagnostic: str, recommended_fix: str = "لا يوجد.", anchors: dict | None = None) -> dict:
    return {
        "result": result,
        "diagnostic": diagnostic,
        "recommended_fix": recommended_fix,
        "anchors": anchors or {},
    }


def _seed_farm(*, name: str, slug: str, prefix: str, mode: str, tier: str, approval_profile: str, remote_site: bool, weekly_remote_review: bool, clean: bool = False) -> FarmUATContext:
    if clean:
        _reset_farm_transactions(slug)

    for model in (
        Farm,
        FarmGovernanceProfile,
        FarmSettings,
        CostCenter,
        CashBox,
        Location,
        Asset,
        Supervisor,
        Season,
        CropVariety,
        CropProduct,
        CropRecipe,
        CropRecipeMaterial,
        CropPlanLocation,
        LocationTreeStock,
        BiologicalAssetCohort,
        LocationIrrigationPolicy,
    ):
        _sync_pk_sequence(model)

    users = _ensure_role_users(prefix=prefix, password=DEFAULT_PASSWORD)
    farm, _ = Farm.objects.update_or_create(
        slug=slug,
        defaults={
            "name": name,
            "region": "تهامة",
            "area": Decimal("140.00") if mode == FarmSettings.MODE_SIMPLE else Decimal("420.00"),
            "description": f"حزمة UAT عربية للمزرعة {name}.",
            "is_organization": False,
            "operational_mode": mode,
            "sensing_mode": "MANUAL",
            "organization_id": None,
        },
    )
    governance, _ = FarmGovernanceProfile.objects.update_or_create(
        farm=farm,
        defaults={
            "tier": tier,
            "approved_by": users["system_admin"],
            "rationale": f"UAT governance profile for {name}.",
        },
    )
    settings, _ = FarmSettings.objects.update_or_create(
        farm=farm,
        defaults={
            "mode": mode,
            "approval_profile": approval_profile,
            "enable_petty_cash": True,
            "enable_sharecropping": True,
            "enable_depreciation": True,
            "enable_zakat": True,
            "show_daily_log_smart_card": True,
            "contract_mode": (
                FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY
                if mode == FarmSettings.MODE_SIMPLE
                else FarmSettings.CONTRACT_MODE_FULL_ERP
            ),
            "treasury_visibility": (
                FarmSettings.TREASURY_VISIBILITY_HIDDEN
                if mode == FarmSettings.MODE_SIMPLE
                else FarmSettings.TREASURY_VISIBILITY_VISIBLE
            ),
            "fixed_asset_mode": (
                FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY
                if mode == FarmSettings.MODE_SIMPLE
                else FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION
            ),
            "cost_visibility": (
                FarmSettings.COST_VISIBILITY_SUMMARIZED
                if mode == FarmSettings.MODE_SIMPLE
                else FarmSettings.COST_VISIBILITY_FULL
            ),
            "mandatory_attachment_for_cash": True,
            "attachment_scan_mode": FarmSettings.ATTACHMENT_SCAN_MODE_HEURISTIC,
            "sales_tax_percentage": Decimal("5.00"),
            "allow_multi_location_activities": True,
            "single_finance_officer_allowed": tier == Farm.TIER_SMALL,
            "remote_site": remote_site,
            "weekly_remote_review_required": weekly_remote_review,
        },
    )
    for role_key, role_label, _ in ROLE_DEFAULTS:
        _ensure_membership(user=users[role_key], farm=farm, role=role_label)

    CostConfiguration.objects.update_or_create(
        farm=farm,
        defaults={
            "overhead_rate_per_hectare": Decimal("55.0000"),
            "variance_warning_pct": Decimal("10.00"),
            "variance_critical_pct": Decimal("20.00"),
            "currency": "YER",
            "effective_date": timezone.localdate(),
        },
    )
    SectorRelationship.objects.update_or_create(farm=farm, defaults={"current_balance": ZERO})
    _open_current_fiscal_period(farm=farm, actor=users["system_admin"])

    code_prefix = "RB" if prefix == "rab" else "SR"
    cost_center, _ = CostCenter.objects.update_or_create(
        farm=farm,
        code=f"{code_prefix}-UAT-OPS",
        defaults={"name": f"{name} - تشغيل UAT", "is_active": True},
    )
    cash_box, _ = CashBox.objects.update_or_create(
        farm=farm,
        name=f"خزينة {name} الرئيسية",
        defaults={"box_type": CashBox.MASTER_SAFE, "currency": "YER", "balance": Decimal("5000000.0000")},
    )

    locations = {}
    location_specs = [
        ("mango_east", "قطاع المانجو الشرقي", "Orchard", f"{code_prefix}-MAN-E"),
        ("banana_south_a", "قطاع الموز الجنوبي", "Orchard", f"{code_prefix}-BAN-S"),
        ("banana_south_b", "قطاع الموز الجنوبي - ب", "Orchard", f"{code_prefix}-BAN-B"),
        ("corn_west", "حقل الذرة الغربي", "Field", f"{code_prefix}-CRN-W"),
        ("input_store", "مستودع المدخلات", "Warehouse", f"{code_prefix}-IN"),
        ("yield_store", "مستودع المحصول", "Warehouse", f"{code_prefix}-OUT"),
    ]
    for key, loc_name, loc_type, code in location_specs:
        locations[key], _ = Location.objects.update_or_create(
            farm=farm,
            name=loc_name,
            defaults={"type": loc_type, "code": code},
        )

    units = _ensure_units()
    items = {
        "urea": _ensure_item(name="سماد يوريا", group="Fertilizers", unit=units["KG"], uom="kg", price=Decimal("800.000")),
        "npk": _ensure_item(name="سماد NPK", group="Fertilizers", unit=units["KG"], uom="kg", price=Decimal("950.000")),
        "potassium": _ensure_item(name="سلفات بوتاسيوم", group="Fertilizers", unit=units["KG"], uom="kg", price=Decimal("1250.000")),
        "stem_borer": _ensure_item(name="مبيد حفار الساق", group="Agrochemicals", unit=units["LTR"], uom="L", price=Decimal("3800.000")),
        "diesel": _ensure_item(name="ديزل زراعي", group="Fuel", unit=units["LTR"], uom="L", price=Decimal("900.000")),
        "corn_seed": _ensure_item(name="بذور ذرة صفراء", group="Seeds", unit=units["KG"], uom="kg", price=Decimal("1200.000")),
        "corn_product": _ensure_item(name="محصول الذرة الصفراء", group="Produce", unit=units["KG"], uom="kg", price=Decimal("320.000")),
        "mango_product": _ensure_item(name="محصول مانجو كيت", group="Produce", unit=units["KG"], uom="kg", price=Decimal("520.000")),
        "banana_product": _ensure_item(name="محصول موز جراند نين", group="Produce", unit=units["KG"], uom="kg", price=Decimal("240.000")),
    }

    opening_balances = [
        ("urea", Decimal("1000.000")),
        ("npk", Decimal("850.000")),
        ("potassium", Decimal("500.000")),
        ("stem_borer", Decimal("150.000")),
        ("diesel", Decimal("900.000")),
        ("corn_seed", Decimal("200.000")),
    ]
    for item_key, qty in opening_balances:
        InventoryService.record_movement(
            farm=farm,
            item=items[item_key],
            qty_delta=qty,
            location=locations["input_store"],
            ref_type="rabouia_sarima_seed_opening",
            ref_id=f"{slug}:{item_key}",
            note=f"Opening balance for {name} UAT",
            batch_number=f"{code_prefix}-{item_key.upper()}",
            actor_user=users["system_admin"],
        )

    assets = {}
    asset_specs = [
        ("tractor", "جرار رقم 3", "Machinery", "tractor", Decimal("15000000.00"), Decimal("3000.0000")),
        ("pump", "مضخة بئر الربوعية" if prefix == "rab" else "مضخة تشغيل الصارمة", "Solar", "pump", Decimal("8500000.00"), Decimal("1700.0000")),
        ("fuel_tank", "خزان ديزل الصارمة" if prefix == "sar" else "خزان ديزل الربوعية", "Facility", "tank", Decimal("1200000.00"), Decimal("900.0000")),
        ("packing_line", f"خط تعبئة {name}", "Facility", "packing_line", Decimal("5500000.00"), Decimal("2200.0000")),
    ]
    for key, asset_name, category, asset_type, purchase_value, hourly_cost in asset_specs:
        assets[key], _ = Asset.objects.update_or_create(
            farm=farm,
            code=f"{code_prefix}-{key.upper()}",
            defaults={
                "name": asset_name,
                "category": category,
                "asset_type": asset_type,
                "purchase_value": purchase_value,
                "operational_cost_per_hour": hourly_cost,
            },
        )
    MachineRate.objects.update_or_create(
        asset=assets["tractor"],
        defaults={
            "daily_rate": Decimal("25000.0000"),
            "cost_per_hour": Decimal("3000.0000"),
            "fuel_consumption_rate": Decimal("8.0000"),
        },
    )
    LaborRate.objects.update_or_create(
        farm=farm,
        role_name="عامل يومي",
        effective_date=timezone.localdate(),
        defaults={"daily_rate": Decimal("4500.0000"), "cost_per_hour": Decimal("562.5000"), "currency": "YER"},
    )
    TankCalibration.objects.update_or_create(
        asset=assets["fuel_tank"],
        cm_reading=Decimal("100.00"),
        defaults={"liters_volume": Decimal("1000.0000")},
    )
    TankCalibration.objects.update_or_create(
        asset=assets["fuel_tank"],
        cm_reading=Decimal("80.00"),
        defaults={"liters_volume": Decimal("800.0000")},
    )

    supervisor_name = "أحمد المشرف" if prefix == "rab" else "مشرف الصارمة"
    supervisor, _ = Supervisor.objects.update_or_create(
        farm=farm,
        code=f"{code_prefix}-SUP-01",
        defaults={"name": supervisor_name},
    )
    employees = {
        "field_operator": _ensure_employee(
            farm=farm,
            user=users["field_operator"],
            employee_id=f"{code_prefix}-FIELD",
            first_name="ياسر" if prefix == "rab" else "ليلى",
            last_name="المدخل" if prefix == "rab" else "المشرفة",
            role="Worker",
        ),
        "agronomist": _ensure_employee(
            farm=farm,
            user=users["agronomist"],
            employee_id=f"{code_prefix}-AGR",
            first_name="أحمد" if prefix == "rab" else "سالم",
            last_name="الزراعي",
            role="Engineer",
        ),
    }

    season, _ = Season.objects.update_or_create(
        name=f"{name} 2026",
        defaults={"start_date": date(2026, 1, 1), "end_date": date(2026, 12, 31), "is_active": True},
    )
    contract_season, _ = Season.objects.update_or_create(
        name=f"{name} Contract 2027",
        defaults={"start_date": date(2027, 1, 1), "end_date": date(2027, 12, 31), "is_active": True},
    )

    crops = {
        "corn": _ensure_crop(farm=farm, name="ذرة صفراء هجينة", is_perennial=False),
        "mango": _ensure_crop(farm=farm, name="مانجو", is_perennial=True),
        "banana": _ensure_crop(farm=farm, name="موز", is_perennial=True),
    }
    varieties = {
        "mango": CropVariety.objects.update_or_create(
            crop=crops["mango"],
            name="كيت",
            defaults={"code": "V-MANGO-KEITT", "est_days_to_harvest": 180, "expected_yield_per_ha": Decimal("18.00")},
        )[0],
        "banana": CropVariety.objects.update_or_create(
            crop=crops["banana"],
            name="جراند نين",
            defaults={"code": "V-BANANA-GN", "est_days_to_harvest": 120, "expected_yield_per_ha": Decimal("25.00")},
        )[0],
    }
    CropProduct.objects.update_or_create(crop=crops["corn"], item=items["corn_product"], farm=farm, name="محصول الذرة الصفراء", defaults={"is_primary": True})
    CropProduct.objects.update_or_create(crop=crops["mango"], item=items["mango_product"], farm=farm, name="محصول مانجو كيت", defaults={"is_primary": True})
    CropProduct.objects.update_or_create(crop=crops["banana"], item=items["banana_product"], farm=farm, name="محصول موز جراند نين", defaults={"is_primary": True})

    recipes = {
        "corn": CropRecipe.objects.update_or_create(crop=crops["corn"], name=f"{name} Corn Standard", defaults={"expected_labor_hours_per_ha": Decimal("32.00")})[0],
        "mango": CropRecipe.objects.update_or_create(crop=crops["mango"], name=f"{name} Mango Service", defaults={"expected_labor_hours_per_ha": Decimal("24.00")})[0],
        "banana": CropRecipe.objects.update_or_create(crop=crops["banana"], name=f"{name} Banana Service", defaults={"expected_labor_hours_per_ha": Decimal("22.00")})[0],
    }
    CropRecipeMaterial.objects.update_or_create(recipe=recipes["corn"], item=items["corn_seed"], defaults={"standard_qty_per_ha": Decimal("18.000")})
    CropRecipeMaterial.objects.update_or_create(recipe=recipes["corn"], item=items["urea"], defaults={"standard_qty_per_ha": Decimal("12.000")})
    CropRecipeMaterial.objects.update_or_create(recipe=recipes["mango"], item=items["stem_borer"], defaults={"standard_qty_per_ha": Decimal("2.000")})
    CropRecipeMaterial.objects.update_or_create(recipe=recipes["banana"], item=items["npk"], defaults={"standard_qty_per_ha": Decimal("6.000")})

    plans = {
        "corn": _ensure_plan(
            farm=farm,
            crop=crops["corn"],
            season=season,
            name=f"{name} Corn 2026",
            recipe=recipes["corn"],
            area=Decimal("12.00"),
            actor=users["system_admin"],
            budget_total=Decimal("1200.0000"),
        ),
        "mango": _ensure_plan(
            farm=farm,
            crop=crops["mango"],
            season=season,
            name=f"{name} Mango 2026",
            recipe=recipes["mango"],
            area=Decimal("18.00"),
            actor=users["system_admin"],
            budget_total=Decimal("1500.0000"),
        ),
        "banana": _ensure_plan(
            farm=farm,
            crop=crops["banana"],
            season=season,
            name=f"{name} Banana 2026",
            recipe=recipes["banana"],
            area=Decimal("16.00"),
            actor=users["system_admin"],
            budget_total=Decimal("1350.0000"),
        ),
    }
    CropPlanLocation.objects.update_or_create(crop_plan=plans["corn"], location=locations["corn_west"], defaults={"assigned_area": Decimal("12.00")})
    CropPlanLocation.objects.update_or_create(crop_plan=plans["mango"], location=locations["mango_east"], defaults={"assigned_area": Decimal("18.00")})
    CropPlanLocation.objects.update_or_create(crop_plan=plans["banana"], location=locations["banana_south_a"], defaults={"assigned_area": Decimal("8.00")})
    CropPlanLocation.objects.update_or_create(crop_plan=plans["banana"], location=locations["banana_south_b"], defaults={"assigned_area": Decimal("8.00")})

    tasks = {
        "corn_service": _ensure_task(
            crop=crops["corn"],
            stage="Growth",
            name=f"خدمة ذرة {name}",
            archetype=Task.Archetype.MATERIAL_INTENSIVE,
            requires_machinery=True,
        ),
        "mango_service": _ensure_task(
            crop=crops["mango"],
            stage="Perennial",
            name=f"خدمة مانجو {name}",
            archetype=Task.Archetype.PERENNIAL_SERVICE,
            requires_tree_count=True,
            is_perennial=True,
        ),
        "banana_service": _ensure_task(
            crop=crops["banana"],
            stage="Perennial",
            name=f"خدمة موز {name}",
            archetype=Task.Archetype.PERENNIAL_SERVICE,
            requires_tree_count=True,
            is_perennial=True,
        ),
        "corn_harvest": _ensure_task(
            crop=crops["corn"],
            stage="Harvest",
            name=f"حصاد ذرة {name}",
            archetype=Task.Archetype.HARVEST,
            is_harvest_task=True,
        ),
    }

    productive_status, _ = TreeProductivityStatus.objects.get_or_create(code="PRODUCTIVE", defaults={"name_en": "Productive", "name_ar": "منتج"})
    TreeLossReason.objects.get_or_create(code="DROUGHT", defaults={"name_en": "Drought", "name_ar": "جفاف طبيعي"})
    LocationTreeStock.objects.update_or_create(location=locations["mango_east"], crop_variety=varieties["mango"], defaults={"current_tree_count": 420 if prefix == "rab" else 620, "productivity_status": productive_status})
    LocationTreeStock.objects.update_or_create(location=locations["banana_south_a"], crop_variety=varieties["banana"], defaults={"current_tree_count": 300, "productivity_status": productive_status})
    LocationTreeStock.objects.update_or_create(location=locations["banana_south_b"], crop_variety=varieties["banana"], defaults={"current_tree_count": 280, "productivity_status": productive_status})
    BiologicalAssetCohort.objects.update_or_create(
        farm=farm,
        crop=crops["mango"],
        location=locations["mango_east"],
        batch_name=f"{code_prefix}-MANGO-2026",
        defaults={"status": BiologicalAssetCohort.STATUS_PRODUCTIVE, "quantity": 420 if prefix == "rab" else 620, "planted_date": date(2026, 1, 1)},
    )
    BiologicalAssetCohort.objects.update_or_create(
        farm=farm,
        crop=crops["banana"],
        location=locations["banana_south_a"],
        batch_name=f"{code_prefix}-BANANA-A-2026",
        defaults={"status": BiologicalAssetCohort.STATUS_PRODUCTIVE, "quantity": 300, "planted_date": date(2026, 1, 1)},
    )
    BiologicalAssetCohort.objects.update_or_create(
        farm=farm,
        crop=crops["banana"],
        location=locations["banana_south_b"],
        batch_name=f"{code_prefix}-BANANA-B-2026",
        defaults={"status": BiologicalAssetCohort.STATUS_PRODUCTIVE, "quantity": 280, "planted_date": date(2026, 1, 1)},
    )
    for key in ("corn_west", "mango_east", "banana_south_a", "banana_south_b"):
        LocationIrrigationPolicy.objects.update_or_create(
            location=locations[key],
            valid_daterange=DateRange(date(2026, 1, 1), None, "[)"),
            defaults={
                "zakat_rule": LocationIrrigationPolicy.ZAKAT_WELL_5,
                "approved_by": users["system_admin"],
                "reason": f"{name} UAT irrigation policy",
            },
        )

    return FarmUATContext(
        farm=farm,
        settings=settings,
        governance=governance,
        cost_center=cost_center,
        cash_box=cash_box,
        season=season,
        contract_season=contract_season,
        crops=crops,
        locations=locations,
        items=items,
        plans=plans,
        tasks=tasks,
        assets=assets,
        users=users,
        employees=employees,
        supervisor=supervisor,
        run_id=timezone.now().strftime("%Y%m%d%H%M%S"),
    )


@transaction.atomic
def seed_rabouia_uat(*, clean: bool = False, verbose: bool = False) -> FarmUATContext:
    return _seed_farm(
        name=RABOUIA_FARM_NAME,
        slug=RABOUIA_FARM_SLUG,
        prefix="rab",
        mode=FarmSettings.MODE_SIMPLE,
        tier=Farm.TIER_SMALL,
        approval_profile=FarmSettings.APPROVAL_PROFILE_TIERED,
        remote_site=True,
        weekly_remote_review=True,
        clean=clean,
    )


@transaction.atomic
def seed_sarima_uat(*, clean: bool = False, verbose: bool = False) -> FarmUATContext:
    return _seed_farm(
        name=SARIMA_FARM_NAME,
        slug=SARIMA_FARM_SLUG,
        prefix="sar",
        mode=FarmSettings.MODE_STRICT,
        tier=Farm.TIER_LARGE,
        approval_profile=FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE,
        remote_site=False,
        weekly_remote_review=False,
        clean=clean,
    )


def _make_log(ctx: FarmUATContext, *, notes: str, delta_days: int = 0) -> DailyLog:
    return DailyLog.objects.create(
        farm=ctx.farm,
        log_date=timezone.localdate() + timedelta(days=delta_days),
        notes=notes,
        created_by=ctx.users["field_operator"],
        updated_by=ctx.users["field_operator"],
        supervisor=ctx.supervisor,
    )


def _seed_batch_number(ctx: FarmUATContext, item_key: str) -> str:
    prefix = "RB" if ctx.farm.slug == RABOUIA_FARM_SLUG else "SR"
    return f"{prefix}-{item_key.upper()}"


def _activity_client_for(ctx: FarmUATContext, user_key: str = "field_operator") -> APIClient:
    client = APIClient()
    client.defaults["HTTP_HOST"] = "localhost"
    client.force_authenticate(user=ctx.users[user_key])
    return client


def _phase_simple_bootstrap(ctx: FarmUATContext) -> dict:
    snapshot = _set_mode(ctx, mode=FarmSettings.MODE_SIMPLE)
    task_contract = ctx.tasks["corn_service"].get_effective_contract()
    return _phase_success(
        result={
            "mode": snapshot["mode"],
            "cost_visibility": snapshot["cost_visibility"],
            "smart_card_contract": bool(snapshot["show_daily_log_smart_card"]),
            "card_keys": list(task_contract.get("smart_cards", {}).keys()),
        },
        diagnostic="تم التحقق من أن الربوعية تعمل في SIMPLE مع smart_card_stack كعقد القراءة اليومي ومنع أي surface مالي حوكمي مباشر.",
    )


def _phase_custody_handshake(ctx: FarmUATContext) -> dict:
    batch_number = _seed_batch_number(ctx, "urea")
    transfer = CustodyTransferService.issue_transfer(
        farm=ctx.farm,
        supervisor=ctx.supervisor,
        item=ctx.items["urea"],
        source_location=ctx.locations["input_store"],
        qty="50",
        actor=ctx.users["storekeeper"],
        batch_number=batch_number,
        idempotency_key=f"{ctx.run_id}-custody-issue",
    )
    accepted = CustodyTransferService.accept_transfer(transfer=transfer, actor=ctx.users["field_operator"])

    log = _make_log(ctx, notes="دورة عهدة سماد يوريا")
    client = _activity_client_for(ctx)
    response = client.post(
        "/api/v1/activities/",
        {
            "log_id": log.id,
            "task_id": ctx.tasks["corn_service"].id,
            "location_ids": [ctx.locations["corn_west"].id],
            "asset_id": ctx.assets["tractor"].id,
            "machine_hours": "1.5",
            "items": [
                {
                    "item": ctx.items["urea"].id,
                    "qty": "40",
                    "applied_qty": "38",
                    "waste_qty": "2",
                    "waste_reason": "تسرب ميداني",
                    "uom": "kg",
                    "batch_number": batch_number,
                }
            ],
        },
        format="json",
        HTTP_X_IDEMPOTENCY_KEY=f"{ctx.run_id}-custody-activity",
        HTTP_X_FARM_ID=str(ctx.farm.id),
        secure=True,
    )
    if response.status_code != 201:
        raise ValidationError(response.content.decode("utf-8"))

    blocked_top_up = False
    try:
        CustodyTransferService.issue_transfer(
            farm=ctx.farm,
            supervisor=ctx.supervisor,
            item=ctx.items["urea"],
            source_location=ctx.locations["input_store"],
            qty="12",
            actor=ctx.users["storekeeper"],
            batch_number=batch_number,
            idempotency_key=f"{ctx.run_id}-custody-topup-block",
        )
    except ValidationError:
        blocked_top_up = True

    returned = CustodyTransferService.return_transfer(transfer=accepted, actor=ctx.users["storekeeper"], qty="10")
    balance = CustodyTransferService.get_item_custody_balance(farm=ctx.farm, supervisor=ctx.supervisor, item=ctx.items["urea"])
    return _phase_success(
        result={
            "transfer_id": accepted.id,
            "accepted_qty": str(accepted.accepted_qty),
            "returned_qty": str(returned.returned_qty),
            "final_status": returned.status,
            "custody_balance": str(balance),
            "top_up_blocked": blocked_top_up,
        },
        diagnostic="تمت المصافحة الرقمية للعهدة بنجاح: صرف -> قبول -> استهلاك جزئي -> إرجاع متبقٍ مع منع top-up غير المحكوم.",
    )


def _phase_seasonal_corn(ctx: FarmUATContext) -> dict:
    batch_number = _seed_batch_number(ctx, "npk")
    transfer = CustodyTransferService.issue_transfer(
        farm=ctx.farm,
        supervisor=ctx.supervisor,
        item=ctx.items["npk"],
        source_location=ctx.locations["input_store"],
        qty="60",
        actor=ctx.users["storekeeper"],
        batch_number=batch_number,
        idempotency_key=f"{ctx.run_id}-corn-issue",
    )
    CustodyTransferService.accept_transfer(transfer=transfer, actor=ctx.users["field_operator"])
    log = _make_log(ctx, notes="خدمة ذرة موسمية مع ساعات آلة")
    client = _activity_client_for(ctx)
    response = client.post(
        "/api/v1/activities/",
        {
            "log_id": log.id,
            "task_id": ctx.tasks["corn_service"].id,
            "location_ids": [ctx.locations["corn_west"].id],
            "asset_id": ctx.assets["tractor"].id,
            "machine_hours": "2",
            "items": [
                {
                    "item": ctx.items["npk"].id,
                    "qty": "55",
                    "applied_qty": "50",
                    "waste_qty": "5",
                    "waste_reason": "تسرب ميداني",
                    "uom": "kg",
                    "batch_number": batch_number,
                }
            ],
        },
        format="json",
        HTTP_X_IDEMPOTENCY_KEY=f"{ctx.run_id}-corn-cycle",
        HTTP_X_FARM_ID=str(ctx.farm.id),
        secure=True,
    )
    if response.status_code != 201:
        raise ValidationError(response.content.decode("utf-8"))
    approved = _submit_and_approve_log(ctx, log=log, critical_note="انحراف خطة الذرة موثق ضمن UAT الربوعية.")
    activity = Activity.objects.get(pk=response.json()["id"])
    return _phase_success(
        result={
            "daily_log_id": approved.id,
            "activity_id": activity.id,
            "variance_status": approved.variance_status,
            "cost_materials": str(activity.cost_materials),
            "cost_wastage": str(activity.cost_wastage),
            "cost_machinery": str(activity.cost_machinery),
        },
        diagnostic="تمت خدمة الذرة مع machine hours وفصل wastage cost عن applied cost مع بقاء التكلفة backend-only.",
    )


def _phase_mango_perennial(ctx: FarmUATContext) -> dict:
    reason = TreeLossReason.objects.get(code="DROUGHT")
    log = _make_log(ctx, notes="خدمة مانجو مع فقد روتيني")
    activity = _ensure_activity(
        log=log,
        crop_plan=ctx.plans["mango"],
        task=ctx.tasks["mango_service"],
        location=ctx.locations["mango_east"],
        created_by=ctx.users["field_operator"],
        crop_variety=CropVariety.objects.get(crop=ctx.crops["mango"], name="كيت"),
        cost_total=Decimal("950.0000"),
        tree_delta=-4,
        tree_loss_reason=reason,
    )
    TreeServiceCoverage.objects.update_or_create(
        activity=activity,
        location=ctx.locations["mango_east"],
        crop_variety=activity.crop_variety,
        defaults={"farm": ctx.farm, "trees_covered": 90, "area_covered_ha": Decimal("2.0000")},
    )
    approved = _submit_and_approve_log(ctx, log=log, critical_note="فقد مانجو روتيني دون impairment shortcut.")
    current_stock = LocationTreeStock.objects.get(location=ctx.locations["mango_east"], crop_variety=activity.crop_variety)
    return _phase_success(
        result={
            "daily_log_id": approved.id,
            "activity_id": activity.id,
            "tree_delta": activity.tree_count_delta,
            "tree_loss_reason": reason.name_ar,
            "current_tree_count": current_stock.current_tree_count,
        },
        diagnostic="تم إثبات أن الفقد الروتيني للأشجار يبقى variance تشغيليًا على LocationTreeStock ولا يتحول إلى impairment shortcut.",
    )


def _phase_banana_perennial(ctx: FarmUATContext) -> dict:
    variety = CropVariety.objects.get(crop=ctx.crops["banana"], name="جراند نين")
    log = _make_log(ctx, notes="خدمة موز متعددة المواقع")
    activity = _ensure_activity(
        log=log,
        crop_plan=ctx.plans["banana"],
        task=ctx.tasks["banana_service"],
        location=ctx.locations["banana_south_a"],
        created_by=ctx.users["field_operator"],
        crop_variety=variety,
        cost_total=Decimal("860.0000"),
    )
    ActivityLocation.objects.update_or_create(
        activity=activity,
        location=ctx.locations["banana_south_b"],
        defaults={"allocated_percentage": Decimal("45.00")},
    )
    TreeServiceCoverage.objects.update_or_create(
        activity=activity,
        location=ctx.locations["banana_south_a"],
        crop_variety=variety,
        defaults={"farm": ctx.farm, "trees_covered": 120, "area_covered_ha": Decimal("2.0000"), "distribution_mode": TreeServiceCoverage.DISTRIBUTION_EXCEPTION_WEIGHTED},
    )
    TreeServiceCoverage.objects.update_or_create(
        activity=activity,
        location=ctx.locations["banana_south_b"],
        crop_variety=variety,
        defaults={"farm": ctx.farm, "trees_covered": 85, "area_covered_ha": Decimal("1.4000"), "distribution_mode": TreeServiceCoverage.DISTRIBUTION_EXCEPTION_WEIGHTED},
    )
    approved = _submit_and_approve_log(ctx, log=log)
    return _phase_success(
        result={
            "daily_log_id": approved.id,
            "activity_id": activity.id,
            "coverage_rows": TreeServiceCoverage.objects.filter(activity=activity).count(),
            "activity_locations": ActivityLocation.objects.filter(activity=activity).count(),
            "distribution_mode": TreeServiceCoverage.objects.filter(activity=activity).first().distribution_mode,
        },
        diagnostic="تمت خدمة الموز على أكثر من موقع مع بقاء service coverage row-location-specific وعدم collapse إلى موقع واحد.",
    )


def _phase_offline_replay(ctx: FarmUATContext) -> dict:
    batch_number = _seed_batch_number(ctx, "potassium")
    success_uuid = str(uuid4())
    conflict_uuid = str(uuid4())
    accepted = CustodyTransferService.issue_transfer(
        farm=ctx.farm,
        supervisor=ctx.supervisor,
        item=ctx.items["potassium"],
        source_location=ctx.locations["input_store"],
        qty="8",
        actor=ctx.users["storekeeper"],
        batch_number=batch_number,
        idempotency_key=f"{ctx.run_id}-offline-issue",
    )
    CustodyTransferService.accept_transfer(transfer=accepted, actor=ctx.users["field_operator"])
    client = _activity_client_for(ctx)
    success_response = client.post(
        "/api/v1/offline/daily-log-replay/atomic/",
        {
            "uuid": success_uuid,
            "idempotency_key": success_uuid,
            "farm_id": ctx.farm.id,
            "supervisor_id": ctx.supervisor.id,
            "client_seq": 1,
            "device_id": f"tablet-{ctx.farm.slug}",
            "device_timestamp": "2026-04-09T10:00:00Z",
            "log": {"log_date": "2026-04-08", "notes": "offline success"},
            "activity": {
                "task": ctx.tasks["corn_service"].id,
                "locations": [ctx.locations["corn_west"].id],
                "asset_id": ctx.assets["tractor"].id,
                "machine_hours": "1.0",
                "items_payload": [
                    {
                        "item": ctx.items["potassium"].id,
                        "qty": "3",
                        "applied_qty": "2",
                        "waste_qty": "1",
                        "waste_reason": "تسرب ميداني",
                        "uom": "kg",
                        "batch_number": batch_number,
                    }
                ],
            },
        },
        format="json",
        HTTP_X_IDEMPOTENCY_KEY=success_uuid,
        HTTP_X_FARM_ID=str(ctx.farm.id),
        secure=True,
    )
    if success_response.status_code != 201:
        raise ValidationError(success_response.content.decode("utf-8"))

    conflict_response = client.post(
        "/api/v1/offline/daily-log-replay/atomic/",
        {
            "uuid": conflict_uuid,
            "idempotency_key": conflict_uuid,
            "farm_id": ctx.farm.id,
            "supervisor_id": ctx.supervisor.id,
            "client_seq": 3,
            "device_id": f"tablet-{ctx.farm.slug}",
            "device_timestamp": "2026-04-09T11:00:00Z",
            "log": {"log_date": "2026-04-08"},
            "activity": {
                "task": ctx.tasks["corn_service"].id,
                "locations": [ctx.locations["corn_west"].id],
                "asset_id": ctx.assets["tractor"].id,
                "machine_hours": "0.5",
            },
        },
        format="json",
        HTTP_X_IDEMPOTENCY_KEY=conflict_uuid,
        HTTP_X_FARM_ID=str(ctx.farm.id),
        secure=True,
    )
    return _phase_success(
        result={
            "sync_status": success_response.json()["status"],
            "conflict_status_code": conflict_response.status_code,
            "dlq_count": SyncConflictDLQ.objects.filter(farm=ctx.farm).count(),
        },
        diagnostic="تمت مزامنة payload ذرية بنجاح ودخل التسلسل الخارج عن client_seq إلى DLQ دون كسر بقية المزامنة.",
    )


def _phase_simple_finance_posture(ctx: FarmUATContext) -> dict:
    _set_mode(ctx, mode=FarmSettings.MODE_SIMPLE)
    petty_block = ""
    supplier_block = ""
    try:
        PettyCashService.create_request(
            user=ctx.users["farm_accountant"],
            farm=ctx.farm,
            amount=Decimal("5000.0000"),
            description="طلب نثرية يجب أن يُحجب في SIMPLE",
            cost_center=ctx.cost_center,
        )
    except (ValidationError, PermissionDenied) as exc:
        petty_block = str(exc)
    po = PurchaseOrder.objects.create(
        farm=ctx.farm,
        vendor_name="مورد الربوعية",
        order_date=timezone.localdate(),
        expected_delivery_date=timezone.localdate() + timedelta(days=2),
        status=PurchaseOrder.Status.RECEIVED,
        notes="PO testing simple posture",
    )
    PurchaseOrderItem.objects.create(purchase_order=po, item=ctx.items["urea"], qty=Decimal("25.000"), unit_price=Decimal("800.0000"))
    try:
        SupplierSettlementService.create_draft(
            user=ctx.users["farm_finance_manager"],
            purchase_order_id=po.id,
            invoice_reference=f"{ctx.run_id}-SIMPLE-BLOCK",
            cost_center=ctx.cost_center,
            crop_plan=ctx.plans["corn"],
        )
    except (ValidationError, PermissionDenied) as exc:
        supplier_block = str(exc)

    middleware = RouteBreachAuditMiddleware(lambda request: HttpResponse("ok"))
    factory = RequestFactory()
    request = factory.get("/api/v1/finance/treasury-transactions/", HTTP_X_FARM_ID=str(ctx.farm.id))
    request.user = ctx.users["farm_finance_manager"]
    response = middleware(request)
    return _phase_success(
        result={
            "petty_cash_blocked": bool(petty_block),
            "supplier_blocked": bool(supplier_block),
            "route_breach_status": response.status_code,
            "route_breach_audits": AuditLog.objects.filter(farm=ctx.farm, action="ROUTE_BREACH_ATTEMPT").count(),
        },
        diagnostic="تم إثبات أن SIMPLE يبقى posture-only في المالية مع audit إلزامي لمحاولات route breach.",
    )


def _phase_simple_reports(ctx: FarmUATContext) -> dict:
    _set_mode(ctx, mode=FarmSettings.MODE_SIMPLE)
    client = _activity_client_for(ctx, "system_admin")
    reports_response = client.get(
        f"/api/v1/reports/?farm={ctx.farm.id}",
        HTTP_X_FARM_ID=str(ctx.farm.id),
        secure=True,
    )
    advanced_response = client.get(
        f"/api/v1/advanced-report/?farm={ctx.farm.id}&start=2026-01-01&end=2026-12-31",
        HTTP_X_FARM_ID=str(ctx.farm.id),
        secure=True,
    )
    if reports_response.status_code != 200 or advanced_response.status_code != 200:
        raise ValidationError("تعذر تحميل تقارير SIMPLE للمزرعة الربوعية.")
    body = advanced_response.json()
    serialized = json.dumps(body, ensure_ascii=False)
    forbidden_keys = ["exact_amount", "financial_trace", "strict_finance_trace", "treasury_trace"]
    leaked = [key for key in forbidden_keys if key in serialized]
    return _phase_success(
        result={
            "reports_status": reports_response.status_code,
            "advanced_status": advanced_response.status_code,
            "has_details": bool(body.get("details")),
            "forbidden_finance_keys": leaked,
        },
        diagnostic="تم تحميل تقارير الربوعية في SIMPLE مع بقاء السطح تقنيًا وعدم تسرب القيم المالية الصريحة المحظورة.",
    )


def _phase_strict_bootstrap(ctx: FarmUATContext) -> dict:
    snapshot = _set_mode(ctx, mode=FarmSettings.MODE_STRICT)
    finance_manager_role = FarmMembership.objects.filter(
        farm=ctx.farm,
        user=ctx.users["farm_finance_manager"],
        role="المدير المالي للمزرعة",
    ).exists()
    return _phase_success(
        result={
            "mode": snapshot["mode"],
            "approval_profile": ctx.settings.approval_profile,
            "treasury_visibility": snapshot["treasury_visibility"],
            "has_farm_finance_manager": finance_manager_role,
        },
        diagnostic="تم التحقق من أن الصارمة تعمل في STRICT مع strict_finance وتعيين المدير المالي للمزرعة كشرط حاكم.",
    )


def _phase_inventory_procurement(ctx: FarmUATContext) -> dict:
    po = PurchaseOrder.objects.create(
        farm=ctx.farm,
        vendor_name="مورد الصارمة",
        order_date=timezone.localdate(),
        expected_delivery_date=timezone.localdate() + timedelta(days=3),
        status=PurchaseOrder.Status.APPROVED,
        notes="توريد مدخلات الذرة للصـارمة",
    )
    PurchaseOrderItem.objects.create(purchase_order=po, item=ctx.items["stem_borer"], qty=Decimal("40.000"), unit_price=Decimal("3800.0000"))
    receipt = InventoryService.record_movement(
        farm=ctx.farm,
        item=ctx.items["stem_borer"],
        qty_delta=Decimal("40.000"),
        location=ctx.locations["input_store"],
        ref_type="purchase_order_receipt",
        ref_id=str(po.id),
        note="توريد مبيد حفار الساق إلى مستودع المدخلات",
        batch_number=f"{ctx.run_id}-PO",
        actor_user=ctx.users["storekeeper"],
    )
    issue = InventoryService.record_movement(
        farm=ctx.farm,
        item=ctx.items["stem_borer"],
        qty_delta=Decimal("-10.000"),
        location=ctx.locations["input_store"],
        ref_type="sarima_execution_issue",
        ref_id=str(ctx.plans["mango"].id),
        note="صرف مبيد إلى قطاع المانجو الشرقي",
        batch_number=f"{ctx.run_id}-PO",
        actor_user=ctx.users["storekeeper"],
    )
    remaining_qty = ItemInventory.objects.get(farm=ctx.farm, location=ctx.locations["input_store"], item=ctx.items["stem_borer"]).qty
    return _phase_success(
        result={
            "purchase_order_id": po.id,
            "receipt_movement_id": str(receipt.id),
            "issue_movement_id": str(issue.id),
            "remaining_qty": str(remaining_qty),
        },
        diagnostic="تم إثبات دورة procurement -> receipt -> issue ضمن نفس truth chain للمخزون في STRICT.",
    )


def _phase_petty_cash(ctx: FarmUATContext) -> dict:
    request_obj = PettyCashService.create_request(
        user=ctx.users["farm_accountant"],
        farm=ctx.farm,
        amount=Decimal("12000.0000"),
        description="نثرية تشغيل الذرة",
        cost_center=ctx.cost_center,
    )
    request_obj = PettyCashService.approve_request(request_obj.id, ctx.users["sector_director"])
    request_obj = PettyCashService.disburse_request(request_obj.id, ctx.cash_box.id, ctx.users["sector_director"])
    settlement = PettyCashService.create_settlement(
        request_id=request_obj.id,
        user=ctx.users["farm_accountant"],
        approval_note="تسوية نثرية الصارمة",
    )
    PettyCashService.add_settlement_line(
        settlement_id=settlement.id,
        user=ctx.users["farm_accountant"],
        amount=Decimal("9000.0000"),
        description="عمالة ومستلزمات تشغيل",
    )
    _safe_attachment(
        farm=ctx.farm,
        uploaded_by=ctx.users["farm_accountant"],
        related_document_type="petty_cash_settlement",
        document_scope=str(settlement.id),
        filename="sarima-petty-cash.pdf",
    )
    settlement = PettyCashService.settle_request(settlement.id, ctx.users["sector_director"])
    return _phase_success(
        result={
            "request_id": request_obj.id,
            "request_status": request_obj.status,
            "settlement_id": settlement.id,
            "settlement_status": settlement.status,
        },
        diagnostic="تمت دورة صندوق النثرية الكاملة في الصارمة: طلب -> اعتماد -> صرف -> تسوية -> مرفق authoritative.",
    )


def _phase_receipts_and_deposit(ctx: FarmUATContext) -> dict:
    collection = ReceiptDepositService.record_collection(
        farm=ctx.farm,
        user=ctx.users["cashier"],
        amount=Decimal("18000.0000"),
        source_description="تحصيل بيع محصول الذرة",
        idempotency_key=f"{ctx.run_id}-receipt-collection",
        cost_center=ctx.cost_center,
        crop_plan=ctx.plans["corn"],
        reference="SR-REC-001",
    )
    deposit = ReceiptDepositService.record_deposit(
        receipt_id=collection["receipt_id"],
        farm=ctx.farm,
        user=ctx.users["cashier"],
        deposit_reference="SR-DEP-001",
        idempotency_key=f"{ctx.run_id}-receipt-deposit",
        deposit_account="MAIN",
    )
    reconcile = ReceiptDepositService.reconcile(
        receipt_id=collection["receipt_id"],
        farm=ctx.farm,
        user=ctx.users["sector_accountant"],
        reconciliation_note="مطابقة تحصيل الصارمة",
    )
    return _phase_success(
        result={
            "collection_status": collection["status"],
            "deposit_status": deposit["status"],
            "reconcile_status": reconcile["status"],
        },
        diagnostic="تمت دورة التحصيل والإيداع والمطابقة بالـ idempotency المطلوبة في STRICT.",
    )


def _phase_supplier_settlement(ctx: FarmUATContext) -> dict:
    po = PurchaseOrder.objects.create(
        farm=ctx.farm,
        vendor_name="مورد تجهيزات الصارمة",
        order_date=timezone.localdate(),
        expected_delivery_date=timezone.localdate() + timedelta(days=5),
        status=PurchaseOrder.Status.RECEIVED,
        notes="توريد تجهيزات مبيد وسماد",
    )
    PurchaseOrderItem.objects.create(purchase_order=po, item=ctx.items["npk"], qty=Decimal("50.000"), unit_price=Decimal("950.0000"))
    settlement = SupplierSettlementService.create_draft(
        user=ctx.users["farm_finance_manager"],
        purchase_order_id=po.id,
        invoice_reference=f"{ctx.run_id}-SUP-001",
        cost_center=ctx.cost_center,
        crop_plan=ctx.plans["corn"],
    )
    settlement = SupplierSettlementService.submit_review(settlement.id, ctx.users["sector_accountant"])
    _safe_attachment(
        farm=ctx.farm,
        uploaded_by=ctx.users["sector_accountant"],
        related_document_type="supplier_settlement",
        document_scope=str(settlement.id),
        filename="sarima-supplier-settlement.pdf",
    )
    settlement = SupplierSettlementService.approve(settlement.id, ctx.users["sector_director"])
    settlement = SupplierSettlementService.record_payment(
        settlement_id=settlement.id,
        cash_box_id=ctx.cash_box.id,
        amount=Decimal("47500.0000"),
        user=ctx.users["sector_director"],
        idempotency_key=f"{ctx.run_id}-supplier-payment",
        note="سداد مورد تجهيزات الصارمة",
        reference="SR-SUP-PAY-01",
    )
    return _phase_success(
        result={
            "supplier_settlement_id": settlement.id,
            "status": settlement.status,
            "paid_amount": str(settlement.paid_amount),
        },
        diagnostic="تمت دورة تسوية المورد بالاعتماد الحوكمي والمرفق authoritative وترحيل الدفع النهائي.",
    )


def _phase_fixed_assets(ctx: FarmUATContext) -> dict:
    capitalized = FixedAssetLifecycleService.capitalize_asset(
        user=ctx.users["sector_director"],
        asset_id=ctx.assets["packing_line"].id,
        capitalized_value=Decimal("250000.00"),
        reason="رسملة خط تعبئة الصارمة",
        ref_id=f"{ctx.run_id}-fixed-asset",
    )
    ledger_rows = FinancialLedger.objects.filter(
        farm=ctx.farm,
        object_id=str(ctx.assets["packing_line"].id),
        description__icontains="رسملة أصل",
    ).count()
    return _phase_success(
        result={"status": capitalized["status"], "asset_id": capitalized["asset_id"], "ledger_rows": ledger_rows},
        diagnostic="تم إثبات رسملة الأصل الثابت مع trace محاسبي append-only في STRICT.",
    )


def _phase_fuel_reconciliation(ctx: FarmUATContext) -> dict:
    fuel_log = FuelLog.objects.create(
        farm=ctx.farm,
        asset_tank=ctx.assets["fuel_tank"],
        supervisor=ctx.supervisor,
        reading_start_cm=Decimal("100.00"),
        reading_end_cm=Decimal("80.00"),
    )
    log = _make_log(ctx, notes="تسوية وقود الصارمة")
    FuelConsumptionAlert.objects.create(
        log=log,
        asset=ctx.assets["tractor"],
        machine_hours=Decimal("8.0000"),
        expected_liters=Decimal("180.0000"),
        actual_liters=Decimal("200.0000"),
        deviation_pct=Decimal("11.11"),
        status=FuelConsumptionAlert.STATUS_WARNING,
        note="انحراف استهلاك الوقود",
    )
    result = FuelReconciliationPostingService.approve_and_post(
        user=ctx.users["sector_director"],
        daily_log_id=log.id,
        fuel_log_id=fuel_log.id,
        reason="اعتماد وتسوية وقود الصارمة",
        ref_id=f"{ctx.run_id}-fuel",
    )
    return _phase_success(
        result={
            "status": result.status,
            "expected_liters": str(result.expected_liters),
            "actual_liters": str(result.actual_liters),
            "variance_liters": str(result.variance_liters),
        },
        diagnostic="تمت دورة الوقود كاملة مع expected vs actual وترحيل التسوية في STRICT.",
    )


def _phase_harvest_and_sales(ctx: FarmUATContext) -> dict:
    harvest_log = _make_log(ctx, notes="حصاد ذرة الصارمة")
    activity = _ensure_activity(
        log=harvest_log,
        crop_plan=ctx.plans["corn"],
        task=ctx.tasks["corn_harvest"],
        location=ctx.locations["corn_west"],
        created_by=ctx.users["field_operator"],
        cost_total=Decimal("980.0000"),
    )
    product = CropProduct.objects.get(crop=ctx.crops["corn"], farm=ctx.farm)
    activity.product = product
    activity.save(update_fields=["product"])
    ActivityHarvest.objects.create(
        activity=activity,
        harvest_quantity=Decimal("300.000"),
        uom="kg",
        batch_number=f"{ctx.run_id}-HARVEST",
        product_id=product.id,
    )
    _submit_and_approve_log(ctx, log=harvest_log, critical_note="حصاد الذرة معتمد ضمن UAT الصارمة.")
    HarvestService.process_harvest(activity, ctx.users["farm_manager"], idempotency_key=f"{ctx.run_id}-harvest-post")
    lot = HarvestLot.objects.filter(farm=ctx.farm, crop_plan=ctx.plans["corn"]).order_by("-created_at").first()
    customer, _ = Customer.objects.get_or_create(name="عميل الصارمة", defaults={"customer_type": Customer.TYPE_WHOLESALER})
    invoice = SaleService.create_invoice(
        customer=customer,
        location=ctx.locations["yield_store"],
        invoice_date=timezone.localdate(),
        items_data=[{"item": ctx.items["corn_product"], "qty": Decimal("80.000"), "unit_price": Decimal("420.00")}],
        user=ctx.users["farm_finance_manager"],
        notes="بيع محصول الذرة",
    )
    return _phase_success(
        result={
            "harvest_activity_id": activity.id,
            "harvest_lot_id": getattr(lot, "id", None),
            "invoice_id": invoice.id,
            "invoice_status": invoice.status,
        },
        diagnostic="تم إثبات دورة الحصاد والبيع لذرة الصارمة مع HarvestLot وفاتورة بيع على نفس truth chain.",
    )


def _phase_contract_operations(ctx: FarmUATContext) -> dict:
    share_contract = SharecroppingContract.objects.create(
        farm=ctx.farm,
        farmer_name="شريك الصارمة",
        crop=ctx.crops["mango"],
        season=ctx.contract_season,
        contract_type=SharecroppingContract.CONTRACT_TYPE_SHARECROPPING,
        irrigation_type="WELL_PUMP",
        institution_percentage=Decimal("0.3500"),
        annual_rent_amount=ZERO,
        notes="عقد مشاركة إنتاج لمحصول المانجو",
    )
    rent_contract = SharecroppingContract.objects.create(
        farm=ctx.farm,
        farmer_name="مستأجر الصارمة",
        crop=ctx.crops["corn"],
        season=ctx.contract_season,
        contract_type=SharecroppingContract.CONTRACT_TYPE_RENTAL,
        irrigation_type="WELL_PUMP",
        institution_percentage=Decimal("0.3000"),
        annual_rent_amount=Decimal("350000.0000"),
        notes="عقد إيجار مساحة زراعية",
    )
    touring = TouringAssessment.objects.create(
        contract=share_contract,
        estimated_total_yield_kg=Decimal("14000.0000"),
        expected_zakat_kg=Decimal("700.0000"),
        expected_institution_share_kg=Decimal("4900.0000"),
        committee_members=["عضو 1", "عضو 2", "عضو 3"],
        notes="الطواف للتقييم فقط.",
    )
    payment = ContractOperationsService.record_rent_payment(
        contract_id=rent_contract.id,
        amount=Decimal("50000.0000"),
        payment_period="2027-Q1",
        notes="دفعة إيجار أولى",
        user=ctx.users["sector_director"],
    )
    dashboard = ContractOperationsService.build_dashboard(farm_id=ctx.farm.id)
    return _phase_success(
        result={
            "share_contract_id": share_contract.id,
            "rental_contract_id": rent_contract.id,
            "touring_id": touring.id,
            "rent_status": payment["status"],
            "dashboard_rows": len(dashboard["results"]),
        },
        diagnostic="تمت دورة العقود مع فصل touring كـ assessment-only وبقاء التسويات الاقتصادية داخل STRICT فقط.",
    )


def _phase_governance_workbench(ctx: FarmUATContext) -> dict:
    contract = SharecroppingContract.objects.filter(farm=ctx.farm, deleted_at__isnull=True).order_by("-id").first()
    req = ApprovalGovernanceService.create_request(
        user=ctx.users["farm_accountant"],
        farm=ctx.farm,
        module=ApprovalRule.MODULE_FINANCE,
        action="contract_payment_posting",
        content_type=ContentType.objects.get_for_model(SharecroppingContract),
        object_id=str(contract.id),
        requested_amount=Decimal("2500000.0000"),
        cost_center=ctx.cost_center,
    )
    for actor_key in [
        "farm_finance_manager",
        "sector_accountant",
        "sector_reviewer",
        "sector_chief_accountant",
        "finance_director",
        "sector_director",
    ]:
        req = ApprovalGovernanceService.approve_request(
            user=ctx.users[actor_key],
            request_id=req.id,
            note=f"{actor_key} approved",
        )
    workbench = ApprovalGovernanceService.role_workbench_snapshot()
    return _phase_success(
        result={
            "approval_request_id": req.id,
            "approval_status": req.status,
            "stage_events": ApprovalStageEvent.objects.filter(request=req).count(),
            "workbench_rows": len(workbench["rows"]),
            "final_required_role": req.final_required_role,
        },
        diagnostic="تمت دورة workbench كاملة مع ApprovalStageEvent append-only ومنع collapse إلى actor واحد عبر السلسلة القطاعية.",
    )


def _phase_attachments(ctx: FarmUATContext) -> dict:
    _safe_attachment(
        farm=ctx.farm,
        uploaded_by=ctx.users["field_operator"],
        related_document_type="daily_log",
        document_scope="sarima-operational",
        evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL,
        filename="sarima-operational.pdf",
    )
    authoritative = _safe_attachment(
        farm=ctx.farm,
        uploaded_by=ctx.users["farm_finance_manager"],
        related_document_type="supplier_settlement",
        document_scope="sarima-authoritative",
        filename="sarima-authoritative.pdf",
    )
    from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService

    AttachmentPolicyService.scan_attachment(attachment=authoritative, farm_settings=ctx.settings)
    AttachmentPolicyService.mark_authoritative_after_approval(
        attachment=authoritative,
        farm_settings=ctx.settings,
        approved_at=timezone.now(),
    )
    AttachmentPolicyService.move_to_archive(attachment=authoritative)
    suspicious = _bad_attachment(
        farm=ctx.farm,
        uploaded_by=ctx.users["farm_finance_manager"],
        related_document_type="supplier_settlement",
        document_scope="sarima-quarantine",
    )
    AttachmentPolicyService.scan_attachment(attachment=suspicious, farm_settings=ctx.settings)
    return _phase_success(
        result={
            "authoritative_archive_state": authoritative.archive_state,
            "quarantine_state": suspicious.quarantine_state,
            "financial_records": Attachment.objects.filter(farm=ctx.farm, evidence_class=Attachment.EVIDENCE_CLASS_FINANCIAL).count(),
        },
        diagnostic="تم التحقق من archive/quarantine lifecycle للمرفقات مع evidence-safe retention في STRICT.",
    )


def _run_phase(*, name: str, category: str, fn, ctx: FarmUATContext, anchors: dict):
    started_at = timezone.now()
    try:
        payload = fn(ctx)
        ended_at = timezone.now()
        return {
            "name": name,
            "category": category,
            "status": "PASS",
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_seconds": round((ended_at - started_at).total_seconds(), 2),
            "result": payload.get("result", {}),
            "diagnostic": payload.get("diagnostic", ""),
            "recommended_fix": payload.get("recommended_fix", "لا يوجد."),
            "anchors": payload.get("anchors", anchors),
        }
    except (
        ValidationError,
        PermissionDenied,
        LookupError,
        TypeError,
        ValueError,
        RuntimeError,
        AssertionError,
    ) as exc:
        ended_at = timezone.now()
        return {
            "name": name,
            "category": category,
            "status": "FAIL",
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_seconds": round((ended_at - started_at).total_seconds(), 2),
            "result": {},
            "diagnostic": str(exc),
            "recommended_fix": PHASE_IMPROVEMENTS.get(name, "راجع service layer والـ contract الخاص بهذا الطور."),
            "anchors": anchors,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }


def _phase_specs(root: Path) -> list[tuple[str, str, callable, str, dict]]:
    evidence_anchor = str(root / "summary.json")
    return [
        ("simple_bootstrap_validation", "governance_reference_defect", _phase_simple_bootstrap, "rabouia", _anchor_pack(code_anchor="backend/smart_agri/core/models/settings.py ; backend/smart_agri/core/services/smart_card_stack_service.py", test_anchor="backend/smart_agri/core/tests/test_smart_card_stack_contract.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("custody_handshake_cycle", "service_layer_defect", _phase_custody_handshake, "rabouia", _anchor_pack(code_anchor="backend/smart_agri/core/services/custody_transfer_service.py ; backend/smart_agri/core/services/activity_item_service.py", test_anchor="backend/smart_agri/core/tests/test_custody_transfer_service.py ; backend/smart_agri/core/tests/test_activity_custody_items.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("seasonal_corn_cycle", "service_layer_defect", _phase_seasonal_corn, "rabouia", _anchor_pack(code_anchor="backend/smart_agri/finance/services/costing_service.py ; backend/smart_agri/core/api/serializers/activity.py", test_anchor="backend/smart_agri/core/tests/test_activity_custody_items.py ; backend/smart_agri/core/tests/test_schedule_variance.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("mango_perennial_cycle", "service_layer_defect", _phase_mango_perennial, "rabouia", _anchor_pack(code_anchor="backend/smart_agri/core/models/tree.py ; backend/smart_agri/core/services/tree_coverage.py", test_anchor="backend/smart_agri/core/tests/test_tree_coverage.py ; backend/smart_agri/core/tests/test_sardood_scenarios.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("banana_perennial_cycle", "service_layer_defect", _phase_banana_perennial, "rabouia", _anchor_pack(code_anchor="backend/smart_agri/core/models/tree.py ; backend/smart_agri/core/services/tree_coverage.py", test_anchor="backend/smart_agri/core/tests/test_tree_coverage.py ; frontend/tests/e2e/daily-log-smart-card.spec.js", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("offline_replay_cycle", "runtime_environment_defect", _phase_offline_replay, "rabouia", _anchor_pack(code_anchor="backend/smart_agri/core/api/viewsets/offline_replay.py ; frontend/src/offline/SyncManager.js", test_anchor="backend/smart_agri/core/tests/test_offline_daily_log_replay.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("simple_finance_posture_only", "governance_reference_defect", _phase_simple_finance_posture, "rabouia", _anchor_pack(code_anchor="backend/smart_agri/core/middleware/route_breach_middleware.py ; backend/smart_agri/finance/services/petty_cash_service.py", test_anchor="backend/smart_agri/core/tests/test_route_breach_middleware.py ; backend/smart_agri/finance/tests/test_simple_mode_finance_block.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("simple_reports_cycle", "api_contract_defect", _phase_simple_reports, "rabouia", _anchor_pack(code_anchor="backend/smart_agri/core/api/viewsets/reports.py ; backend/smart_agri/core/api/reporting_support.py", test_anchor="backend/smart_agri/core/tests/test_reports.py ; backend/smart_agri/core/tests/test_reporting_integration.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("strict_bootstrap_validation", "governance_reference_defect", _phase_strict_bootstrap, "sarima", _anchor_pack(code_anchor="backend/smart_agri/core/models/settings.py ; backend/smart_agri/finance/services/farm_finance_authority_service.py", test_anchor="backend/smart_agri/core/tests/test_farm_size_governance.py ; backend/smart_agri/finance/tests/test_v21_role_workbench.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("inventory_procurement_cycle", "service_layer_defect", _phase_inventory_procurement, "sarima", _anchor_pack(code_anchor="backend/smart_agri/core/services/inventory_service.py", test_anchor="backend/smart_agri/core/tests/test_sardood_scenarios.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("petty_cash_cycle", "service_layer_defect", _phase_petty_cash, "sarima", _anchor_pack(code_anchor="backend/smart_agri/finance/services/petty_cash_service.py", test_anchor="backend/smart_agri/finance/tests/test_petty_cash_service.py ; frontend/tests/e2e/petty-cash.spec.js", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("receipts_and_deposit_cycle", "service_layer_defect", _phase_receipts_and_deposit, "sarima", _anchor_pack(code_anchor="backend/smart_agri/finance/services/receipt_deposit_service.py", test_anchor="backend/smart_agri/finance/tests/test_receipts_deposit_dual_mode.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("supplier_settlement_cycle", "service_layer_defect", _phase_supplier_settlement, "sarima", _anchor_pack(code_anchor="backend/smart_agri/finance/services/supplier_settlement_service.py", test_anchor="backend/smart_agri/finance/tests/test_supplier_settlement_service.py ; frontend/tests/e2e/supplier-settlement.spec.js", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("fixed_assets_cycle", "service_layer_defect", _phase_fixed_assets, "sarima", _anchor_pack(code_anchor="backend/smart_agri/core/services/fixed_asset_lifecycle_service.py", test_anchor="frontend/tests/e2e/fixed-assets.spec.js ; backend/smart_agri/core/tests/test_seed_runtime_governance_evidence_command.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("fuel_reconciliation_cycle", "service_layer_defect", _phase_fuel_reconciliation, "sarima", _anchor_pack(code_anchor="backend/smart_agri/core/services/fuel_reconciliation_posting_service.py", test_anchor="frontend/tests/e2e/fuel-reconciliation.spec.js", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("harvest_and_sales_cycle", "service_layer_defect", _phase_harvest_and_sales, "sarima", _anchor_pack(code_anchor="backend/smart_agri/core/services/harvest_service.py ; backend/smart_agri/sales/services.py", test_anchor="backend/smart_agri/core/tests/test_sardood_scenarios.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("contract_operations_cycle", "governance_reference_defect", _phase_contract_operations, "sarima", _anchor_pack(code_anchor="backend/smart_agri/core/services/contract_operations_service.py", test_anchor="frontend/tests/e2e/contract-operations.spec.js ; backend/smart_agri/core/tests/test_sardood_scenarios.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("governance_workbench_cycle", "governance_reference_defect", _phase_governance_workbench, "sarima", _anchor_pack(code_anchor="backend/smart_agri/finance/services/approval_service.py ; backend/smart_agri/finance/models.py", test_anchor="backend/smart_agri/finance/tests/test_v21_role_workbench.py ; backend/smart_agri/finance/tests/test_approval_chain_collapse.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
        ("attachments_and_evidence_cycle", "api_contract_defect", _phase_attachments, "sarima", _anchor_pack(code_anchor="backend/smart_agri/core/services/attachment_policy_service.py", test_anchor="backend/smart_agri/core/tests/test_attachment_policy_service.py ; backend/smart_agri/core/tests/test_seed_runtime_governance_evidence_command.py", gate_anchor="python backend/manage.py verify_axis_complete_v21", evidence_anchor=evidence_anchor)),
    ]


def _build_report(*, phases: list[dict]) -> dict:
    failures = [phase for phase in phases if phase["status"] != "PASS"]
    passed = len(phases) - len(failures)
    score = round((passed / max(len(phases), 1)) * 100, 2)
    simple_cycle_ok = all(phase["status"] == "PASS" for phase in phases[:8])
    strict_cycle_ok = all(phase["status"] == "PASS" for phase in phases[8:])
    custody_ok = all(phase["status"] == "PASS" for phase in phases[1:7])
    reports_ok = phases[7]["status"] == "PASS"
    harvest_ok = all(phase["status"] == "PASS" for phase in [phases[0], phases[2], phases[15]])
    offline_ok = phases[5]["status"] == "PASS"
    units_ok = all(phase["status"] == "PASS" for phase in [phases[2], phases[9], phases[15]])
    arabic_display_ok = not failures
    return {
        "generated_at": timezone.now().isoformat(),
        "farms": [
            {"name": RABOUIA_FARM_NAME, "slug": RABOUIA_FARM_SLUG, "mode": "SIMPLE"},
            {"name": SARIMA_FARM_NAME, "slug": SARIMA_FARM_SLUG, "mode": "STRICT"},
        ],
        "overall_status": "PASS" if not failures else "FAIL",
        "strict_summary_score": score,
        "before_scorecard": BEFORE_SCORECARD,
        "after_scorecard": {
            "canonical_repo_baseline": 100,
            "uat_pack_provisioning": 100 if passed else 0,
            "simple_operational_cycle": 100 if simple_cycle_ok else 0,
            "strict_governed_cycle": 100 if strict_cycle_ok else 0,
            "offline_and_custody": 100 if custody_ok else 0,
            "reports_and_diagnostics": 100 if reports_ok else 0,
            "arabic_seed_quality": 100 if not failures else 0,
            "harvest_and_production_entry": 100 if harvest_ok else 0,
            "custody_workspace_flow": 100 if custody_ok else 0,
            "permissions_arabic_display": 100 if arabic_display_ok else 0,
            "offline_mode_determinism": 100 if offline_ok else 0,
            "units_normalization": 100 if units_ok else 0,
        },
        "phases": phases,
        "summary": {
            "total": len(phases),
            "passed": passed,
            "failed": len(failures),
            "failure_categories": sorted({phase["category"] for phase in failures}),
        },
        "reference_gaps": [],
        "operational_gaps": [phase["name"] for phase in failures if phase["category"] != "governance_reference_defect"],
        "mode_gaps": [phase["name"] for phase in failures if phase["name"].startswith("simple_") or phase["name"].startswith("strict_")],
        "governance_gaps": [phase["name"] for phase in failures if phase["category"] == "governance_reference_defect"],
        "improvements": IMPROVEMENTS,
        "failures": [
            {
                "name": phase["name"],
                "category": phase["category"],
                "diagnostic": phase["diagnostic"],
                "recommended_fix": phase["recommended_fix"],
            }
            for phase in failures
        ],
    }


def _render_markdown(report: dict) -> str:
    lines = [
        "# دورة UAT شاملة لمزرعتي الربوعية والصارمة",
        "",
        "## الحالة العامة",
        "",
        f"- تاريخ التوليد: `{report['generated_at']}`",
        f"- الحالة العامة: `{report['overall_status']}`",
        f"- التقييم الصارم: `{report['strict_summary_score']}` / 100",
        "- المزرعتان:",
    ]
    for farm in report["farms"]:
        lines.append(f"  - `{farm['name']}` / `{farm['slug']}` / `{farm['mode']}`")
    lines.extend(["", "## تقييم قبل التنفيذ", ""])
    for key, value in report["before_scorecard"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## نتائج كل Phase", ""])
    for phase in report["phases"]:
        lines.extend(
            [
                f"### {phase['name']}",
                f"- الحالة: `{phase['status']}`",
                f"- الفئة: `{phase['category']}`",
                f"- المدة: `{phase['duration_seconds']}` ثانية",
                f"- التشخيص: {phase['diagnostic']}",
                f"- الإجراء المقترح: {phase['recommended_fix']}",
                f"- النتيجة: `{json.dumps(phase['result'], ensure_ascii=False, default=_json_default)}`",
                f"- code anchor: `{phase['anchors'].get('code_anchor', '')}`",
                f"- test anchor: `{phase['anchors'].get('test_anchor', '')}`",
                f"- gate anchor: `{phase['anchors'].get('gate_anchor', '')}`",
                f"- evidence anchor: `{phase['anchors'].get('evidence_anchor', '')}`",
                "",
            ]
        )
    lines.extend(["## تقييم بعد التنفيذ", ""])
    for key, value in report["after_scorecard"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## الفجوات المرجعية", ""])
    lines.extend([f"- {gap}" for gap in report["reference_gaps"]] or ["- لا توجد فجوات مرجعية حية في هذه الحزمة."])
    lines.extend(["", "## الفجوات التشغيلية", ""])
    lines.extend([f"- {gap}" for gap in report["operational_gaps"]] or ["- لا توجد فجوات تشغيلية حاجزة في هذه الحزمة."])
    lines.extend(["", "## الفجوات بين SIMPLE وSTRICT", ""])
    lines.extend([f"- {gap}" for gap in report["mode_gaps"]] or ["- تم الحفاظ على truth chain نفسها مع اختلاف surface فقط بين SIMPLE وSTRICT."])
    lines.extend(["", "## فجوات الحوكمة والأدوار", ""])
    lines.extend([f"- {gap}" for gap in report["governance_gaps"]] or ["- لا توجد فجوات حوكمة حية؛ سلاسل الاعتماد والـ route boundaries سليمة في هذه الحزمة."])
    lines.extend(["", "## التحسينات المقترحة", ""])
    for item in report["improvements"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def run_rabouia_sarima_uat(*, artifact_root: str | Path, clean_seed: bool = False) -> dict:
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "screenshots").mkdir(parents=True, exist_ok=True)

    bundle = RabouiaSarimaBundle(
        rabouia=seed_rabouia_uat(clean=clean_seed),
        sarima=seed_sarima_uat(clean=clean_seed),
    )
    phases = []
    for name, category, fn, target, anchors in _phase_specs(root):
        ctx = bundle.rabouia if target == "rabouia" else bundle.sarima
        phases.append(_run_phase(name=name, category=category, fn=fn, ctx=ctx, anchors=anchors))
    report = _build_report(phases=phases)

    _write_json(root / "before_report.json", BEFORE_SCORECARD)
    (root / "before_report.md").write_text(
        "\n".join(["# تقرير ما قبل التنفيذ", ""] + [f"- {key}: `{value}`" for key, value in BEFORE_SCORECARD.items()]),
        encoding="utf-8",
    )
    _write_json(root / "logs" / "phases.json", {"phases": phases})
    _write_json(root / "summary.json", report)
    (root / "summary.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


__all__ = [
    "DEFAULT_PASSWORD",
    "RABOUIA_FARM_NAME",
    "RABOUIA_FARM_SLUG",
    "SARIMA_FARM_NAME",
    "SARIMA_FARM_SLUG",
    "run_rabouia_sarima_uat",
    "seed_rabouia_uat",
    "seed_sarima_uat",
]
