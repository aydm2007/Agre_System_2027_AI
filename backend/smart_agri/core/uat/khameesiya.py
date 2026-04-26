from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields.ranges import DateRange
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmGovernanceProfile, FarmMembership
from smart_agri.core.models.activity import Activity, ActivityEmployee, ActivityHarvest, ActivityItem, ActivityLocation
from smart_agri.core.models.crop import Crop, CropProduct, CropRecipe, CropRecipeMaterial, CropVariety, FarmCrop
from smart_agri.core.models.farm import Asset, Farm, Location, LocationIrrigationPolicy
from smart_agri.core.models.inventory import BiologicalAssetCohort, HarvestLot
from smart_agri.core.models.log import Attachment, AuditLog, DailyLog, FuelConsumptionAlert, MaterialVarianceAlert
from smart_agri.core.models.partnerships import SharecroppingContract, TouringAssessment
from smart_agri.core.models.planning import CropPlan, CropPlanLocation, Season
from smart_agri.core.models.settings import FarmSettings, LaborRate, MachineRate, Supervisor
from smart_agri.core.models.task import Task
from smart_agri.core.models.tree import LocationTreeStock, TreeLossReason, TreeProductivityStatus, TreeServiceCoverage
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService
from smart_agri.core.services.contract_operations_service import ContractOperationsService
from smart_agri.core.services.fixed_asset_lifecycle_service import FixedAssetLifecycleService
from smart_agri.core.services.fuel_reconciliation_posting_service import FuelReconciliationPostingService
from smart_agri.core.services.harvest_service import HarvestService
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.core.services.log_approval_service import LogApprovalService
from smart_agri.core.services.smart_card_stack_service import build_smart_card_stack
from smart_agri.core.services.variance import compute_log_variance
from smart_agri.finance.models import (
    ApprovalRequest,
    ApprovalRule,
    ApprovalStageEvent,
    CostCenter,
    CostConfiguration,
    FinancialLedger,
    FiscalPeriod,
    FiscalYear,
    SectorRelationship,
)
from smart_agri.finance.models_petty_cash import PettyCashRequest
from smart_agri.finance.models_supplier_settlement import SupplierSettlement
from smart_agri.finance.models_treasury import CashBox
from smart_agri.finance.services.approval_service import ApprovalGovernanceService
from smart_agri.finance.services.petty_cash_service import PettyCashService
from smart_agri.finance.services.receipt_deposit_service import ReceiptDepositService
from smart_agri.finance.services.supplier_settlement_service import SupplierSettlementService
from smart_agri.inventory.models import FuelLog, Item, PurchaseOrder, PurchaseOrderItem, TankCalibration, Unit
from smart_agri.sales.models import Customer
from smart_agri.sales.services import SaleService

User = get_user_model()

KHAMEESIYA_FARM_NAME = "الخميسية"
KHAMEESIYA_FARM_SLUG = "al-khameesiya"
KHAMEESIYA_DEFAULT_PASSWORD = "KhameesiyaUAT#2026"
ZERO = Decimal("0.0000")

BEFORE_SCORECARD = {
    "canonical_axes": 100,
    "release_frozen_baseline": 97,
    "farm_provisioning": 0,
    "seasonal_cycle": 0,
    "mango_cycle": 0,
    "banana_cycle": 0,
    "inventory_procurement": 0,
    "strict_finance": 0,
    "harvest_sales": 0,
    "frontend_dual_mode": 0,
    "end_to_end_new_tenant": 12,
}


@dataclass(slots=True)
class KhameesiyaContext:
    farm: Farm
    settings: FarmSettings
    governance: FarmGovernanceProfile
    cost_center: CostCenter
    cash_box: CashBox
    season: Season
    contract_season: Season
    crops: dict
    locations: dict
    items: dict
    plans: dict
    tasks: dict
    assets: dict
    users: dict
    employees: dict
    supervisor: Supervisor


def _role_defaults() -> list[tuple[str, str, bool]]:
    return [
        ("system_admin", "مدير النظام", True),
        ("farm_manager", "مدير المزرعة", False),
        ("field_operator", "مدخل بيانات", False),
        ("agronomist", "مهندس زراعي", False),
        ("storekeeper", "أمين مخزن", False),
        ("cashier", "أمين صندوق", False),
        ("farm_accountant", "محاسب المزرعة", False),
        ("farm_chief_accountant", "رئيس الحسابات", False),
        ("farm_finance_manager", "المدير المالي للمزرعة", False),
        ("sector_accountant", "محاسب القطاع", False),
        ("sector_reviewer", "مراجع القطاع", False),
        ("sector_chief_accountant", "رئيس حسابات القطاع", False),
        ("finance_director", "المدير المالي لقطاع المزارع", False),
        ("sector_director", "مدير القطاع", False),
    ]


def _ensure_user(*, username: str, display_name: str, is_superuser: bool = False):
    first_name = display_name.split(" ")[0]
    last_name = " ".join(display_name.split(" ")[1:]) or display_name
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": f"{username}@khameesiya.uat.local",
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": True,
            "is_superuser": is_superuser,
        },
    )
    if created or bool(user.is_superuser) != is_superuser:
        user.is_staff = True
        user.is_superuser = is_superuser
        user.set_password(KHAMEESIYA_DEFAULT_PASSWORD)
        user.save()
    return user


def _ensure_membership(*, user, farm, role: str):
    membership, _ = FarmMembership.objects.update_or_create(
        user=user,
        farm=farm,
        defaults={"role": role},
    )
    return membership


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )


def _safe_attachment(
    *,
    farm,
    uploaded_by,
    related_document_type: str,
    document_scope: str,
    evidence_class: str = Attachment.EVIDENCE_CLASS_FINANCIAL,
    filename: str = "khameesiya-proof.pdf",
) -> Attachment:
    file_obj = SimpleUploadedFile(
        filename,
        b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n",
        content_type="application/pdf",
    )
    metadata = AttachmentPolicyService.validate_upload(
        farm_settings=farm.settings,
        file_obj=file_obj,
        evidence_class=evidence_class,
    )
    return Attachment.objects.create(
        file=file_obj,
        name=filename,
        content_type=metadata["content_type"],
        evidence_class=evidence_class,
        uploaded_by=uploaded_by,
        farm=farm,
        document_scope=str(document_scope),
        related_document_type=related_document_type,
        attachment_class=evidence_class,
        retention_class=evidence_class,
        filename_original=metadata["filename_original"],
        mime_type_detected=metadata["mime_type_detected"],
        size_bytes=metadata["size_bytes"],
        size=metadata["size_bytes"],
        content_hash=metadata["content_hash"],
        sha256_checksum=metadata["sha256_checksum"],
        expires_at=metadata["expires_at"],
        storage_tier=metadata["storage_tier"],
        archive_state=metadata["archive_state"],
        malware_scan_status=metadata["malware_scan_status"],
        scan_state=metadata["scan_state"],
        quarantine_state=Attachment.QUARANTINE_STATE_NONE,
    )


def _bad_attachment(*, farm, uploaded_by, related_document_type: str, document_scope: str) -> Attachment:
    filename = "khameesiya-openaction.pdf"
    file_obj = SimpleUploadedFile(
        filename,
        b"%PDF-1.4\n1 0 obj<</OpenAction 2 0 R>>endobj\n%%EOF\n",
        content_type="application/pdf",
    )
    checksum = AttachmentPolicyService._compute_sha256(file_obj)
    return Attachment.objects.create(
        file=file_obj,
        name=filename,
        content_type="application/pdf",
        evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL,
        uploaded_by=uploaded_by,
        farm=farm,
        document_scope=str(document_scope),
        related_document_type=related_document_type,
        attachment_class=Attachment.EVIDENCE_CLASS_OPERATIONAL,
        retention_class=Attachment.EVIDENCE_CLASS_OPERATIONAL,
        filename_original=filename,
        mime_type_detected="application/pdf",
        size_bytes=file_obj.size,
        size=file_obj.size,
        content_hash=checksum,
        sha256_checksum=checksum,
        storage_tier=Attachment.STORAGE_TIER_HOT,
        archive_state=Attachment.ARCHIVE_STATE_HOT,
        malware_scan_status=Attachment.MALWARE_SCAN_PENDING,
        scan_state=Attachment.MALWARE_SCAN_PENDING,
        quarantine_state=Attachment.QUARANTINE_STATE_NONE,
    )


def _set_mode(ctx: KhameesiyaContext, *, mode: str):
    settings = ctx.settings
    if mode == FarmSettings.MODE_SIMPLE:
        settings.mode = FarmSettings.MODE_SIMPLE
        settings.cost_visibility = FarmSettings.COST_VISIBILITY_SUMMARIZED
        settings.contract_mode = FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY
        settings.treasury_visibility = FarmSettings.TREASURY_VISIBILITY_HIDDEN
        settings.fixed_asset_mode = FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY
    else:
        settings.mode = FarmSettings.MODE_STRICT
        settings.cost_visibility = FarmSettings.COST_VISIBILITY_FULL
        settings.contract_mode = FarmSettings.CONTRACT_MODE_FULL_ERP
        settings.treasury_visibility = FarmSettings.TREASURY_VISIBILITY_VISIBLE
        settings.fixed_asset_mode = FarmSettings.FIXED_ASSET_MODE_FULL_CAPITALIZATION
    settings.save()
    ctx.settings = settings
    return settings.policy_snapshot()


def _open_current_fiscal_period(*, farm, actor):
    today = timezone.localdate()
    fy, _ = FiscalYear.objects.get_or_create(
        farm=farm,
        year=today.year,
        defaults={"start_date": date(today.year, 1, 1), "end_date": date(today.year, 12, 31)},
    )
    period_end = (
        date(today.year + (1 if today.month == 12 else 0), 1 if today.month == 12 else today.month + 1, 1)
        - timedelta(days=1)
    )
    period, _ = FiscalPeriod.objects.get_or_create(
        fiscal_year=fy,
        month=today.month,
        defaults={
            "start_date": date(today.year, today.month, 1),
            "end_date": period_end,
            "status": FiscalPeriod.STATUS_OPEN,
            "closed_by": actor,
        },
    )
    if period.status != FiscalPeriod.STATUS_OPEN:
        period.status = FiscalPeriod.STATUS_OPEN
        period.closed_at = None
        period.closed_by = None
        period.save(update_fields=["status", "is_closed", "closed_at", "closed_by", "updated_at"])
    return fy, period


def _ensure_task(
    *,
    crop,
    stage: str,
    name: str,
    archetype: str,
    requires_machinery: bool = False,
    requires_tree_count: bool = False,
    is_perennial: bool = False,
    is_harvest_task: bool = False,
):
    task, _ = Task.objects.update_or_create(
        crop=crop,
        name=name,
        defaults={
            "stage": stage,
            "archetype": archetype,
            "requires_machinery": requires_machinery,
            "requires_tree_count": requires_tree_count,
            "is_perennial_procedure": is_perennial,
            "is_harvest_task": is_harvest_task,
        },
    )
    if not task.task_contract:
        task.task_contract = task.build_default_contract()
        task.save(update_fields=["task_contract", "task_contract_version", "updated_at"])
    return task


def _ensure_activity(
    *,
    log,
    crop_plan,
    task,
    location,
    created_by,
    crop_variety=None,
    cost_total: Decimal = Decimal("0.0000"),
    tree_delta: int = 0,
    tree_loss_reason=None,
) -> Activity:
    activity = Activity.objects.create(
        log=log,
        crop_plan=crop_plan,
        crop=crop_plan.crop,
        task=task,
        created_by=created_by,
        updated_by=created_by,
        cost_materials=ZERO,
        cost_labor=ZERO,
        cost_machinery=ZERO,
        cost_overhead=ZERO,
        cost_total=cost_total.quantize(Decimal("0.0001")),
        days_spent=Decimal("1.00"),
        crop_variety=crop_variety,
        tree_count_delta=tree_delta,
        tree_loss_reason=tree_loss_reason,
        task_contract_snapshot=task.get_effective_contract(),
        task_contract_version=task.task_contract_version or 1,
        data={"seeded_by": "khameesiya_uat"},
    )
    activity.location = location
    activity.save()
    if location is not None:
        ActivityLocation.objects.update_or_create(
            activity=activity,
            location=location,
            defaults={"allocated_percentage": Decimal("100.00")},
        )
    return activity


def _submit_and_approve_log(
    ctx: KhameesiyaContext,
    *,
    log: DailyLog,
    approver_key: str = "farm_manager",
    warning_note: str = "Khameesiya UAT warning reviewed.",
    critical_note: str = "Khameesiya UAT critical variance approved.",
) -> DailyLog:
    submitter = log.created_by or ctx.users["field_operator"]
    approver = ctx.users[approver_key]
    submitted_log = LogApprovalService.submit_log(submitter, log.id)
    variance = compute_log_variance(submitted_log)
    if variance["status"] == "WARNING":
        LogApprovalService.note_warning(approver, log.id, note=warning_note)
    elif variance["status"] == "CRITICAL":
        LogApprovalService.approve_variance(approver, log.id, note=critical_note)
    return LogApprovalService.approve_log(approver, log.id)


def _soft_reset_existing_farm():
    farm = Farm.objects.filter(slug=KHAMEESIYA_FARM_SLUG, deleted_at__isnull=True).first()
    if not farm:
        return
    ActivityEmployee.objects.filter(activity__log__farm=farm).delete()
    ActivityItem.objects.filter(activity__log__farm=farm).delete()
    ActivityHarvest.objects.filter(activity__log__farm=farm).delete()
    FuelConsumptionAlert.objects.filter(log__farm=farm).delete()
    MaterialVarianceAlert.objects.filter(log__farm=farm).delete()
    Activity.objects.filter(log__farm=farm).delete()
    DailyLog.objects.filter(farm=farm).delete()
    ApprovalStageEvent.objects.filter(request__farm=farm).delete()
    ApprovalRequest.objects.filter(farm=farm).delete()
    TouringAssessment.objects.filter(contract__farm=farm).delete()
    SharecroppingContract.objects.filter(farm=farm).delete()
    PurchaseOrderItem.objects.filter(purchase_order__farm=farm).delete()
    PurchaseOrder.objects.filter(farm=farm).delete()
    SupplierSettlement.objects.filter(farm=farm).delete()
    PettyCashRequest.objects.filter(farm=farm).delete()
    Attachment.objects.filter(farm=farm).delete()
    FuelLog.objects.filter(farm=farm).delete()
    HarvestLot.objects.filter(farm=farm).delete()
    AuditLog.objects.filter(farm=farm).delete()


@transaction.atomic
def seed_khameesiya_uat(*, clean: bool = False, verbose: bool = False) -> KhameesiyaContext:
    if clean:
        _soft_reset_existing_farm()

    users: dict[str, User] = {}
    for username, role_label, is_superuser in _role_defaults():
        users[username] = _ensure_user(
            username=username,
            display_name=role_label,
            is_superuser=is_superuser,
        )

    farm, _ = Farm.objects.update_or_create(
        slug=KHAMEESIYA_FARM_SLUG,
        defaults={
            "name": KHAMEESIYA_FARM_NAME,
            "region": "تهامة",
            "area": Decimal("320.00"),
            "description": "مزرعة UAT production-like لاختبار التشغيل الثنائي المود.",
        },
    )
    governance, _ = FarmGovernanceProfile.objects.update_or_create(
        farm=farm,
        defaults={
            "tier": Farm.TIER_LARGE,
            "approved_by": users["system_admin"],
            "rationale": "Khameesiya UAT large-farm governance.",
        },
    )
    settings, _ = FarmSettings.objects.update_or_create(
        farm=farm,
        defaults={
            "mode": FarmSettings.MODE_SIMPLE,
            "approval_profile": FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE,
            "enable_petty_cash": True,
            "enable_sharecropping": True,
            "enable_depreciation": True,
            "enable_zakat": True,
            "show_daily_log_smart_card": True,
            "contract_mode": FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY,
            "treasury_visibility": FarmSettings.TREASURY_VISIBILITY_HIDDEN,
            "fixed_asset_mode": FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY,
            "cost_visibility": FarmSettings.COST_VISIBILITY_SUMMARIZED,
            "mandatory_attachment_for_cash": True,
            "attachment_scan_mode": FarmSettings.ATTACHMENT_SCAN_MODE_HEURISTIC,
            "sales_tax_percentage": Decimal("5.00"),
            "allow_multi_location_activities": True,
            "single_finance_officer_allowed": False,
            "remote_site": False,
            "weekly_remote_review_required": False,
        },
    )

    for _, role_label, _ in _role_defaults():
        username = next(k for k, label, _super in _role_defaults() if label == role_label)
        _ensure_membership(user=users[username], farm=farm, role=role_label)

    CostConfiguration.objects.update_or_create(
        farm=farm,
        defaults={
            "overhead_rate_per_hectare": Decimal("50.0000"),
            "variance_warning_pct": Decimal("10.00"),
            "variance_critical_pct": Decimal("20.00"),
            "currency": "YER",
            "effective_date": timezone.localdate(),
        },
    )
    SectorRelationship.objects.update_or_create(farm=farm, defaults={"current_balance": ZERO})
    _open_current_fiscal_period(farm=farm, actor=users["system_admin"])
    cost_center, _ = CostCenter.objects.update_or_create(
        farm=farm,
        code="KH-UAT-OPS",
        defaults={"name": "الخميسية - تشغيل UAT", "is_active": True},
    )
    cash_box, _ = CashBox.objects.update_or_create(
        farm=farm,
        name="خزينة الخميسية الرئيسية",
        defaults={
            "box_type": CashBox.MASTER_SAFE,
            "currency": "YER",
            "balance": Decimal("5000000.0000"),
        },
    )

    locations = {}
    for key, name, loc_type, code in [
        ("tomato_field", "حقل الطماطم", "Field", "KH-TOM"),
        ("mango_orchard", "بستان المانجو", "Orchard", "KH-MAN"),
        ("banana_orchard", "بستان الموز", "Orchard", "KH-BAN"),
        ("central_store", "المستودع المركزي", "Service", "KH-STO"),
        ("packing_area", "منطقة التعبئة", "Service", "KH-PACK"),
        ("treasury_point", "نقطة الخزينة", "Service", "KH-CASH"),
        ("fuel_point", "نقطة الوقود", "Service", "KH-FUEL"),
    ]:
        locations[key], _ = Location.objects.update_or_create(
            farm=farm,
            name=name,
            defaults={"type": loc_type, "code": code},
        )

    units = {}
    for code, name, symbol, category in [
        ("KG", "كيلوجرام", "kg", Unit.CATEGORY_MASS),
        ("LTR", "لتر", "L", Unit.CATEGORY_VOLUME),
        ("TREE", "شجرة", "tree", Unit.CATEGORY_COUNT),
    ]:
        units[code], _ = Unit.objects.update_or_create(
            code=code,
            defaults={"name": name, "symbol": symbol, "category": category},
        )

    items = {}
    for key, name, group, unit, uom, price in [
        ("urea", "يوريا الخميسية", "Fertilizers", units["KG"], "kg", Decimal("800.000")),
        ("fungicide", "مبيد فطري الخميسية", "Agrochemicals", units["LTR"], "L", Decimal("3500.000")),
        ("diesel", "ديزل الخميسية", "Fuel", units["LTR"], "L", Decimal("900.000")),
        ("tomato_item", "طماطم الخميسية", "Produce", units["KG"], "kg", Decimal("300.000")),
        ("mango_item", "مانجو الخميسية", "Produce", units["KG"], "kg", Decimal("450.000")),
        ("banana_item", "موز الخميسية", "Produce", units["KG"], "kg", Decimal("250.000")),
    ]:
        items[key], _ = Item.objects.update_or_create(
            name=name,
            group=group,
            defaults={"unit": unit, "uom": uom, "unit_price": price, "currency": "YER"},
        )

    for item_key, qty in [
        ("urea", Decimal("1000.000")),
        ("fungicide", Decimal("200.000")),
        ("diesel", Decimal("500.000")),
    ]:
        InventoryService.record_movement(
            farm=farm,
            item=items[item_key],
            qty_delta=qty,
            location=locations["central_store"],
            ref_type="khameesiya_seed_opening",
            ref_id=f"{KHAMEESIYA_FARM_SLUG}:{item_key}",
            note="Opening balance for Khameesiya UAT",
            batch_number=f"OPEN-{item_key.upper()}",
            actor_user=users["system_admin"],
        )

    assets = {}
    for key, name, category, asset_type, purchase_value in [
        ("tractor", "جرار الخميسية", "Machinery", "tractor", Decimal("15000000.00")),
        ("solar_pump", "مضخة شمسية الخميسية", "Solar", "solar_pump", Decimal("8500000.00")),
        ("fuel_tank", "خزان وقود الخميسية", "Facility", "tank", Decimal("1200000.00")),
        ("packing_line", "خط التعبئة الخميسية", "Facility", "packing_line", Decimal("5500000.00")),
    ]:
        assets[key], _ = Asset.objects.update_or_create(
            farm=farm,
            code=f"KH-{key.upper()}",
            defaults={
                "name": name,
                "category": category,
                "asset_type": asset_type,
                "purchase_value": purchase_value,
                "operational_cost_per_hour": Decimal("1500.00"),
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
    Supervisor.objects.update_or_create(
        farm=farm,
        code="KH-SUP-01",
        defaults={"name": "مشرف الخميسية"},
    )
    supervisor = Supervisor.objects.get(farm=farm, code="KH-SUP-01")
    LaborRate.objects.update_or_create(
        farm=farm,
        role_name="عامل يومي",
        effective_date=timezone.localdate(),
        defaults={
            "daily_rate": Decimal("4500.0000"),
            "cost_per_hour": Decimal("562.5000"),
            "currency": "YER",
        },
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

    Employee = __import__("smart_agri.core.models.hr", fromlist=["Employee"]).Employee
    employees = {}
    for key, first, last, role in [
        ("field_operator", "عامل", "الخميسية", "Worker"),
        ("agronomist", "مهندس", "الخميسية", "Engineer"),
    ]:
        employees[key], _ = Employee.objects.update_or_create(
            farm=farm,
            employee_id=f"KH-{key.upper()}",
            defaults={
                "user": users[key],
                "first_name": first,
                "last_name": last,
                "role": role,
                "payment_mode": "SURRA",
                "shift_rate": Decimal("4500.0000"),
                "is_active": True,
            },
        )

    season, _ = Season.objects.update_or_create(
        name="Khameesiya 2026",
        defaults={
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "is_active": True,
        },
    )
    contract_season, _ = Season.objects.update_or_create(
        name="Khameesiya Contract 2027",
        defaults={
            "start_date": date(2027, 1, 1),
            "end_date": date(2027, 12, 31),
            "is_active": True,
        },
    )

    crops = {}
    for key, name, is_perennial, mode in [
        ("tomato", "طماطم الخميسية", False, "Open"),
        ("mango", "مانجو الخميسية", True, "Open"),
        ("banana", "موز الخميسية", True, "Open"),
        ("contract_crop", "ذرة عقود الخميسية", False, "Open"),
    ]:
        crops[key], _ = Crop.objects.update_or_create(
            name=name,
            mode=mode,
            defaults={
                "is_perennial": is_perennial,
                "max_yield_per_ha": Decimal("40.000"),
                "max_yield_per_tree": Decimal("120.000"),
            },
        )
        FarmCrop.objects.get_or_create(farm=farm, crop=crops[key])

    varieties = {
        "mango": CropVariety.objects.update_or_create(
            crop=crops["mango"],
            name="تيمور",
            defaults={
                "code": "KH-MANGO-TIMOR",
                "est_days_to_harvest": 180,
                "expected_yield_per_ha": Decimal("18.00"),
            },
        )[0],
        "banana": CropVariety.objects.update_or_create(
            crop=crops["banana"],
            name="جراند نين",
            defaults={
                "code": "KH-BANANA-GN",
                "est_days_to_harvest": 120,
                "expected_yield_per_ha": Decimal("25.00"),
            },
        )[0],
    }

    CropProduct.objects.update_or_create(
        crop=crops["tomato"],
        item=items["tomato_item"],
        farm=farm,
        name="طماطم الخميسية",
        defaults={"is_primary": True},
    )
    CropProduct.objects.update_or_create(
        crop=crops["mango"],
        item=items["mango_item"],
        farm=farm,
        name="مانجو الخميسية",
        defaults={"is_primary": True},
    )
    CropProduct.objects.update_or_create(
        crop=crops["banana"],
        item=items["banana_item"],
        farm=farm,
        name="موز الخميسية",
        defaults={"is_primary": True},
    )

    recipes = {
        "tomato": CropRecipe.objects.update_or_create(
            crop=crops["tomato"],
            name="Tomato Standard",
            defaults={"expected_labor_hours_per_ha": Decimal("40.00")},
        )[0],
        "mango": CropRecipe.objects.update_or_create(
            crop=crops["mango"],
            name="Mango Service",
            defaults={"expected_labor_hours_per_ha": Decimal("25.00")},
        )[0],
        "banana": CropRecipe.objects.update_or_create(
            crop=crops["banana"],
            name="Banana Service",
            defaults={"expected_labor_hours_per_ha": Decimal("22.00")},
        )[0],
    }
    CropRecipeMaterial.objects.update_or_create(
        recipe=recipes["tomato"],
        item=items["urea"],
        defaults={"standard_qty_per_ha": Decimal("10.000")},
    )
    CropRecipeMaterial.objects.update_or_create(
        recipe=recipes["mango"],
        item=items["fungicide"],
        defaults={"standard_qty_per_ha": Decimal("2.000")},
    )
    CropRecipeMaterial.objects.update_or_create(
        recipe=recipes["banana"],
        item=items["fungicide"],
        defaults={"standard_qty_per_ha": Decimal("1.500")},
    )

    plans = {
        "tomato": CropPlan.objects.update_or_create(
            farm=farm,
            crop=crops["tomato"],
            season=season,
            name="Khameesiya Tomato 2026",
            defaults={
                "recipe": recipes["tomato"],
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 12, 31),
                "area": Decimal("12.00"),
                "status": "ACTIVE",
                "budget_total": Decimal("1000.0000"),
                "budget_materials": Decimal("400.0000"),
                "budget_labor": Decimal("300.0000"),
                "budget_machinery": Decimal("300.0000"),
                "currency": "YER",
                "created_by": users["system_admin"],
            },
        )[0],
        "mango": CropPlan.objects.update_or_create(
            farm=farm,
            crop=crops["mango"],
            season=season,
            name="Khameesiya Mango 2026",
            defaults={
                "recipe": recipes["mango"],
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 12, 31),
                "area": Decimal("20.00"),
                "status": "ACTIVE",
                "budget_total": Decimal("1500.0000"),
                "budget_materials": Decimal("500.0000"),
                "budget_labor": Decimal("500.0000"),
                "budget_machinery": Decimal("500.0000"),
                "currency": "YER",
                "created_by": users["system_admin"],
            },
        )[0],
        "banana": CropPlan.objects.update_or_create(
            farm=farm,
            crop=crops["banana"],
            season=season,
            name="Khameesiya Banana 2026",
            defaults={
                "recipe": recipes["banana"],
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 12, 31),
                "area": Decimal("16.00"),
                "status": "ACTIVE",
                "budget_total": Decimal("1200.0000"),
                "budget_materials": Decimal("500.0000"),
                "budget_labor": Decimal("350.0000"),
                "budget_machinery": Decimal("350.0000"),
                "currency": "YER",
                "created_by": users["system_admin"],
            },
        )[0],
    }
    CropPlanLocation.objects.update_or_create(
        crop_plan=plans["tomato"],
        location=locations["tomato_field"],
        defaults={"assigned_area": Decimal("12.00")},
    )
    CropPlanLocation.objects.update_or_create(
        crop_plan=plans["mango"],
        location=locations["mango_orchard"],
        defaults={"assigned_area": Decimal("20.00")},
    )
    CropPlanLocation.objects.update_or_create(
        crop_plan=plans["banana"],
        location=locations["banana_orchard"],
        defaults={"assigned_area": Decimal("16.00")},
    )

    tasks = {
        "tomato_service": _ensure_task(
            crop=crops["tomato"],
            stage="Growth",
            name="خدمة طماطم الخميسية",
            archetype=Task.Archetype.MATERIAL_INTENSIVE,
            requires_machinery=True,
        ),
        "mango_service": _ensure_task(
            crop=crops["mango"],
            stage="Perennial",
            name="خدمة مانجو الخميسية",
            archetype=Task.Archetype.PERENNIAL_SERVICE,
            requires_tree_count=True,
            is_perennial=True,
        ),
        "banana_service": _ensure_task(
            crop=crops["banana"],
            stage="Perennial",
            name="خدمة موز الخميسية",
            archetype=Task.Archetype.PERENNIAL_SERVICE,
            requires_tree_count=True,
            is_perennial=True,
        ),
        "tomato_harvest": _ensure_task(
            crop=crops["tomato"],
            stage="Harvest",
            name="حصاد طماطم الخميسية",
            archetype=Task.Archetype.HARVEST,
            is_harvest_task=True,
        ),
    }

    productive_status, _ = TreeProductivityStatus.objects.get_or_create(
        code="PRODUCTIVE",
        defaults={"name_en": "Productive", "name_ar": "منتج"},
    )
    TreeLossReason.objects.get_or_create(
        code="DROUGHT",
        defaults={"name_en": "Drought", "name_ar": "جفاف طبيعي"},
    )

    LocationTreeStock.objects.update_or_create(
        location=locations["mango_orchard"],
        crop_variety=varieties["mango"],
        defaults={"current_tree_count": 500, "productivity_status": productive_status},
    )
    LocationTreeStock.objects.update_or_create(
        location=locations["banana_orchard"],
        crop_variety=varieties["banana"],
        defaults={"current_tree_count": 750, "productivity_status": productive_status},
    )
    BiologicalAssetCohort.objects.update_or_create(
        farm=farm,
        crop=crops["mango"],
        location=locations["mango_orchard"],
        batch_name="KH-MANGO-2026",
        defaults={
            "status": BiologicalAssetCohort.STATUS_PRODUCTIVE,
            "quantity": 500,
            "planted_date": date(2026, 1, 1),
        },
    )
    BiologicalAssetCohort.objects.update_or_create(
        farm=farm,
        crop=crops["banana"],
        location=locations["banana_orchard"],
        batch_name="KH-BANANA-2026",
        defaults={
            "status": BiologicalAssetCohort.STATUS_PRODUCTIVE,
            "quantity": 750,
            "planted_date": date(2026, 1, 1),
        },
    )

    for loc_key in ("tomato_field", "mango_orchard", "banana_orchard"):
        LocationIrrigationPolicy.objects.update_or_create(
            location=locations[loc_key],
            valid_daterange=DateRange(date(2026, 1, 1), None, "[)"),
            defaults={
                "zakat_rule": LocationIrrigationPolicy.ZAKAT_WELL_5,
                "approved_by": users["system_admin"],
                "reason": "Khameesiya UAT irrigation policy",
            },
        )

    return KhameesiyaContext(
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
    )


def _simple_bootstrap_phase(ctx: KhameesiyaContext) -> dict:
    snapshot = _set_mode(ctx, mode=FarmSettings.MODE_SIMPLE)
    client = APIClient()
    client.force_authenticate(user=ctx.users["field_operator"])
    return {
        "mode": snapshot["mode"],
        "cost_visibility": snapshot["cost_visibility"],
        "smart_card_contract": bool(snapshot["show_daily_log_smart_card"]),
        "service_card_keys": list(
            ctx.tasks["tomato_service"].get_effective_contract().get("smart_cards", {}).keys()
        ),
    }


def _create_tomato_cycle(ctx: KhameesiyaContext) -> dict:
    tomato_log = DailyLog.objects.create(
        farm=ctx.farm,
        log_date=timezone.localdate() - timedelta(days=3),
        notes="Khameesiya tomato cycle",
        created_by=ctx.users["field_operator"],
        updated_by=ctx.users["field_operator"],
        supervisor=ctx.supervisor,
    )
    activity = _ensure_activity(
        log=tomato_log,
        crop_plan=ctx.plans["tomato"],
        task=ctx.tasks["tomato_service"],
        location=ctx.locations["tomato_field"],
        created_by=ctx.users["field_operator"],
        cost_total=Decimal("1800.0000"),
    )
    InventoryService.record_movement(
        farm=ctx.farm,
        item=ctx.items["urea"],
        qty_delta=Decimal("-80.000"),
        location=ctx.locations["central_store"],
        ref_type="khameesiya_internal_issue",
        ref_id=str(activity.id),
        note="Transfer urea to tomato field for Khameesiya UAT",
        batch_number="OPEN-UREA",
        actor_user=ctx.users["storekeeper"],
    )
    InventoryService.record_movement(
        farm=ctx.farm,
        item=ctx.items["urea"],
        qty_delta=Decimal("80.000"),
        location=ctx.locations["tomato_field"],
        ref_type="khameesiya_internal_receipt",
        ref_id=str(activity.id),
        note="Receive urea at tomato field for Khameesiya UAT",
        batch_number="OPEN-UREA",
        actor_user=ctx.users["storekeeper"],
    )
    ActivityItem.objects.create(
        activity=activity,
        item=ctx.items["urea"],
        qty=Decimal("55.000"),
        uom="kg",
        batch_number="OPEN-UREA",
        cost_per_unit=Decimal("800.0000"),
        total_cost=Decimal("44000.0000"),
    )
    ActivityEmployee.objects.create(
        activity=activity,
        employee=ctx.employees["field_operator"],
        surrah_share=Decimal("1.00"),
    )
    approved_log = _submit_and_approve_log(
        ctx,
        log=tomato_log,
        critical_note="Intentional critical tomato variance for UAT.",
    )
    stack = build_smart_card_stack(activity)
    return {
        "daily_log_id": approved_log.id,
        "activity_id": activity.id,
        "variance_status": approved_log.variance_status,
        "smart_card_keys": [row.get("card_key") for row in stack],
    }


def _create_mango_cycle(ctx: KhameesiyaContext) -> dict:
    mango_log = DailyLog.objects.create(
        farm=ctx.farm,
        log_date=timezone.localdate() - timedelta(days=2),
        notes="Khameesiya mango service",
        created_by=ctx.users["field_operator"],
        updated_by=ctx.users["field_operator"],
        supervisor=ctx.supervisor,
    )
    tree_loss_reason = TreeLossReason.objects.get(code="DROUGHT")
    stock = LocationTreeStock.objects.get(
        location=ctx.locations["mango_orchard"],
        crop_variety=CropVariety.objects.get(crop=ctx.crops["mango"], name="تيمور"),
    )
    activity = _ensure_activity(
        log=mango_log,
        crop_plan=ctx.plans["mango"],
        task=ctx.tasks["mango_service"],
        location=ctx.locations["mango_orchard"],
        created_by=ctx.users["field_operator"],
        crop_variety=CropVariety.objects.get(crop=ctx.crops["mango"], name="تيمور"),
        cost_total=Decimal("900.0000"),
        tree_delta=-5,
        tree_loss_reason=tree_loss_reason,
    )
    TreeServiceCoverage.objects.update_or_create(
        activity=activity,
        location=ctx.locations["mango_orchard"],
        crop_variety=activity.crop_variety,
        defaults={"farm": ctx.farm, "trees_covered": 120, "area_covered_ha": Decimal("2.4000")},
    )
    ActivityEmployee.objects.create(
        activity=activity,
        employee=ctx.employees["agronomist"],
        surrah_share=Decimal("1.00"),
    )
    approved_log = _submit_and_approve_log(
        ctx,
        log=mango_log,
        critical_note="Khameesiya mango variance approved by manager.",
    )
    return {
        "daily_log_id": approved_log.id,
        "activity_id": activity.id,
        "tree_delta": activity.tree_count_delta,
        "current_tree_count": stock.current_tree_count,
        "tree_loss_reason": tree_loss_reason.name_ar,
    }


def _create_banana_cycle(ctx: KhameesiyaContext) -> dict:
    banana_log = DailyLog.objects.create(
        farm=ctx.farm,
        log_date=timezone.localdate() - timedelta(days=1),
        notes="Khameesiya banana service",
        created_by=ctx.users["field_operator"],
        updated_by=ctx.users["field_operator"],
        supervisor=ctx.supervisor,
    )
    activity = _ensure_activity(
        log=banana_log,
        crop_plan=ctx.plans["banana"],
        task=ctx.tasks["banana_service"],
        location=ctx.locations["banana_orchard"],
        created_by=ctx.users["field_operator"],
        crop_variety=CropVariety.objects.get(crop=ctx.crops["banana"], name="جراند نين"),
        cost_total=Decimal("850.0000"),
    )
    TreeServiceCoverage.objects.update_or_create(
        activity=activity,
        location=ctx.locations["banana_orchard"],
        crop_variety=activity.crop_variety,
        defaults={"farm": ctx.farm, "trees_covered": 180, "area_covered_ha": Decimal("3.0000")},
    )
    approved_log = _submit_and_approve_log(
        ctx,
        log=banana_log,
        critical_note="Khameesiya banana variance approved by manager.",
    )
    return {
        "daily_log_id": approved_log.id,
        "activity_id": activity.id,
        "variety": activity.crop_variety.name,
        "service_rows": TreeServiceCoverage.objects.filter(activity=activity).count(),
    }


def _inventory_and_procurement_phase(ctx: KhameesiyaContext) -> dict:
    po = PurchaseOrder.objects.create(
        farm=ctx.farm,
        vendor_name="مورد الخميسية",
        order_date=timezone.localdate(),
        expected_delivery_date=timezone.localdate() + timedelta(days=3),
        status=PurchaseOrder.Status.APPROVED,
        notes="Khameesiya UAT PO",
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        item=ctx.items["fungicide"],
        qty=Decimal("120.000"),
        unit_price=Decimal("3500.0000"),
    )
    receipt = InventoryService.record_movement(
        farm=ctx.farm,
        item=ctx.items["fungicide"],
        qty_delta=Decimal("120.000"),
        location=ctx.locations["central_store"],
        ref_type="purchase_order_receipt",
        ref_id=str(po.id),
        note="Khameesiya purchase receipt",
        batch_number="PO-KH-FUNGI",
        actor_user=ctx.users["storekeeper"],
    )
    issue = InventoryService.record_movement(
        farm=ctx.farm,
        item=ctx.items["fungicide"],
        qty_delta=Decimal("-25.000"),
        location=ctx.locations["central_store"],
        ref_type="activity_issue",
        ref_id=str(ctx.plans["mango"].id),
        note="Khameesiya issue to mango cycle",
        batch_number="PO-KH-FUNGI",
        actor_user=ctx.users["storekeeper"],
    )
    inventory_qty = Item.objects.get(pk=ctx.items["fungicide"].pk).inventories.get(
        farm=ctx.farm,
        location=ctx.locations["central_store"],
    ).qty
    return {
        "purchase_order_id": po.id,
        "receipt_movement_id": str(receipt.id),
        "issue_movement_id": str(issue.id),
        "remaining_qty": inventory_qty,
    }


def _simple_posture_phase(ctx: KhameesiyaContext) -> dict:
    _set_mode(ctx, mode=FarmSettings.MODE_SIMPLE)
    petty_cash_block = ""
    supplier_block = ""
    try:
        PettyCashService.create_request(
            user=ctx.users["farm_accountant"],
            farm=ctx.farm,
            amount=Decimal("5000.0000"),
            description="Should block in SIMPLE",
            cost_center=ctx.cost_center,
        )
    except (ValidationError, PermissionDenied) as exc:
        petty_cash_block = str(exc)
    try:
        po = PurchaseOrder.objects.filter(farm=ctx.farm, deleted_at__isnull=True).order_by("-id").first()
        SupplierSettlementService.create_draft(
            user=ctx.users["farm_finance_manager"],
            purchase_order_id=po.id,
            invoice_reference="SIMPLE-BLOCK",
            cost_center=ctx.cost_center,
            crop_plan=ctx.plans["tomato"],
        )
    except (ValidationError, PermissionDenied) as exc:
        supplier_block = str(exc)
    return {
        "petty_cash_blocked": bool(petty_cash_block),
        "supplier_settlement_blocked": bool(supplier_block),
        "petty_cash_message": petty_cash_block[:240],
        "supplier_message": supplier_block[:240],
    }


def _strict_transition_phase(ctx: KhameesiyaContext) -> dict:
    snapshot = _set_mode(ctx, mode=FarmSettings.MODE_STRICT)
    activity = Activity.objects.filter(log__farm=ctx.farm, crop_plan=ctx.plans["tomato"]).first()
    stack = build_smart_card_stack(activity)
    return {
        "mode": snapshot["mode"],
        "contract_mode": snapshot["contract_mode"],
        "treasury_visibility": snapshot["treasury_visibility"],
        "smart_card_count": len(stack),
    }


def _strict_finance_phase(ctx: KhameesiyaContext) -> dict:
    _set_mode(ctx, mode=FarmSettings.MODE_STRICT)
    petty_request = PettyCashService.create_request(
        user=ctx.users["farm_accountant"],
        farm=ctx.farm,
        amount=Decimal("12000.0000"),
        description="Khameesiya petty cash request",
        cost_center=ctx.cost_center,
    )
    petty_request = PettyCashService.approve_request(petty_request.id, ctx.users["sector_director"])
    petty_request = PettyCashService.disburse_request(
        petty_request.id,
        ctx.cash_box.id,
        ctx.users["sector_director"],
    )
    settlement = PettyCashService.create_settlement(
        request_id=petty_request.id,
        user=ctx.users["farm_accountant"],
        approval_note="Khameesiya settlement",
    )
    PettyCashService.add_settlement_line(
        settlement_id=settlement.id,
        user=ctx.users["farm_accountant"],
        amount=Decimal("9000.0000"),
        description="Operational petty cash settlement",
    )
    _safe_attachment(
        farm=ctx.farm,
        uploaded_by=ctx.users["farm_accountant"],
        related_document_type="petty_cash_settlement",
        document_scope=str(settlement.id),
    )
    settlement = PettyCashService.settle_request(settlement.id, ctx.users["sector_director"])

    po = PurchaseOrder.objects.filter(farm=ctx.farm, deleted_at__isnull=True).order_by("-id").first()
    supplier = SupplierSettlementService.create_draft(
        user=ctx.users["farm_finance_manager"],
        purchase_order_id=po.id,
        invoice_reference="KH-SUP-2026-01",
        cost_center=ctx.cost_center,
        crop_plan=ctx.plans["tomato"],
    )
    supplier = SupplierSettlementService.submit_review(supplier.id, ctx.users["sector_accountant"])
    _safe_attachment(
        farm=ctx.farm,
        uploaded_by=ctx.users["sector_accountant"],
        related_document_type="supplier_settlement",
        document_scope=str(supplier.id),
    )
    supplier = SupplierSettlementService.approve(supplier.id, ctx.users["sector_director"])
    supplier_payment_key = f"KH-SUP-PAY-{ctx.farm.id}-{supplier.id}"
    supplier = SupplierSettlementService.record_payment(
        settlement_id=supplier.id,
        cash_box_id=ctx.cash_box.id,
        amount=Decimal("100000.0000"),
        user=ctx.users["sector_director"],
        idempotency_key=supplier_payment_key,
        note="Khameesiya supplier payment",
        reference="KH-SUP-REF-01",
    )

    receipt_collection_key = f"KH-RD-COL-{ctx.farm.id}-{po.id}"
    collection = ReceiptDepositService.record_collection(
        farm=ctx.farm,
        user=ctx.users["cashier"],
        amount=Decimal("15000.0000"),
        source_description="Khameesiya customer collection",
        idempotency_key=receipt_collection_key,
        cost_center=ctx.cost_center,
        crop_plan=ctx.plans["tomato"],
        reference="KH-RD-001",
    )
    receipt_deposit_key = f"KH-RD-DEP-{ctx.farm.id}-{po.id}"
    deposit = ReceiptDepositService.record_deposit(
        receipt_id=collection["receipt_id"],
        farm=ctx.farm,
        user=ctx.users["cashier"],
        deposit_reference="KH-DEP-001",
        idempotency_key=receipt_deposit_key,
        deposit_account="MAIN",
    )
    reconcile = ReceiptDepositService.reconcile(
        receipt_id=collection["receipt_id"],
        farm=ctx.farm,
        user=ctx.users["sector_accountant"],
        reconciliation_note="Khameesiya receipt reconciled",
    )

    fixed_asset = FixedAssetLifecycleService.capitalize_asset(
        user=ctx.users["sector_director"],
        asset_id=ctx.assets["packing_line"].id,
        capitalized_value=Decimal("250000.00"),
        reason="Khameesiya UAT capitalization",
        ref_id="KH-FA-01",
    )

    fuel_log = FuelLog.objects.create(
        farm=ctx.farm,
        asset_tank=ctx.assets["fuel_tank"],
        supervisor=ctx.supervisor,
        reading_start_cm=Decimal("100.00"),
        reading_end_cm=Decimal("80.00"),
    )
    fuel_daily_log = DailyLog.objects.create(
        farm=ctx.farm,
        log_date=timezone.localdate(),
        notes="Khameesiya fuel reconciliation",
        created_by=ctx.users["field_operator"],
        updated_by=ctx.users["field_operator"],
    )
    FuelConsumptionAlert.objects.create(
        log=fuel_daily_log,
        asset=ctx.assets["tractor"],
        machine_hours=Decimal("8.0000"),
        expected_liters=Decimal("180.0000"),
        actual_liters=Decimal("200.0000"),
        deviation_pct=Decimal("11.11"),
        status=FuelConsumptionAlert.STATUS_WARNING,
        note="Khameesiya fuel variance",
    )
    fuel_post = FuelReconciliationPostingService.approve_and_post(
        user=ctx.users["sector_director"],
        daily_log_id=fuel_daily_log.id,
        fuel_log_id=fuel_log.id,
        reason="Khameesiya strict fuel posting",
        ref_id="KH-FUEL-01",
    )

    return {
        "petty_cash_request_id": petty_request.id,
        "petty_cash_settlement_id": settlement.id,
        "supplier_settlement_id": supplier.id,
        "receipt_status": collection["status"],
        "deposit_status": deposit["status"],
        "reconcile_status": reconcile["status"],
        "fixed_asset_status": fixed_asset["status"],
        "fuel_status": fuel_post.status,
    }


def _harvest_sales_phase(ctx: KhameesiyaContext) -> dict:
    harvest_log = DailyLog.objects.create(
        farm=ctx.farm,
        log_date=timezone.localdate(),
        notes="Khameesiya tomato harvest",
        created_by=ctx.users["field_operator"],
        updated_by=ctx.users["field_operator"],
    )
    harvest_activity = _ensure_activity(
        log=harvest_log,
        crop_plan=ctx.plans["tomato"],
        task=ctx.tasks["tomato_harvest"],
        location=ctx.locations["tomato_field"],
        created_by=ctx.users["field_operator"],
        cost_total=Decimal("950.0000"),
    )
    harvest_activity.product = CropProduct.objects.get(crop=ctx.crops["tomato"], farm=ctx.farm)
    harvest_activity.save(update_fields=["product"])
    ActivityHarvest.objects.create(
        activity=harvest_activity,
        harvest_quantity=Decimal("250.000"),
        uom="kg",
        batch_number="KH-HARVEST-01",
        product_id=harvest_activity.product.id,
    )
    _submit_and_approve_log(
        ctx,
        log=harvest_log,
        critical_note="Khameesiya harvest variance approved by manager.",
    )
    HarvestService.process_harvest(
        harvest_activity,
        ctx.users["farm_manager"],
        idempotency_key="KH-HARVEST-POST-01",
    )
    lot = HarvestLot.objects.filter(farm=ctx.farm, crop_plan=ctx.plans["tomato"]).order_by("-created_at").first()
    customer, _ = Customer.objects.get_or_create(
        name="عميل الخميسية",
        defaults={"customer_type": Customer.TYPE_WHOLESALER},
    )
    invoice = SaleService.create_invoice(
        customer=customer,
        location=ctx.locations["tomato_field"],
        invoice_date=timezone.localdate(),
        items_data=[{"item": ctx.items["tomato_item"], "qty": Decimal("50.000"), "unit_price": Decimal("500.00")}],
        user=ctx.users["farm_finance_manager"],
        notes="Khameesiya tomato sale",
    )
    first_line = invoice.items.first()
    if first_line:
        first_line.harvest_lot = lot
        first_line.batch_number = getattr(lot, "lot_number", "") or "KH-HARVEST-01"
        first_line.save(update_fields=["harvest_lot", "batch_number"])
    SaleService.confirm_sale(invoice, user=ctx.users["sector_director"])
    return {
        "harvest_activity_id": harvest_activity.id,
        "harvest_lot_id": getattr(lot, "id", None),
        "invoice_id": invoice.id,
        "invoice_status": invoice.status,
    }


def _contract_operations_phase(ctx: KhameesiyaContext) -> dict:
    contract = SharecroppingContract.objects.create(
        farm=ctx.farm,
        farmer_name="شريك الخميسية",
        crop=ctx.crops["contract_crop"],
        season=ctx.contract_season,
        contract_type=SharecroppingContract.CONTRACT_TYPE_RENTAL,
        irrigation_type="WELL_PUMP",
        institution_percentage=Decimal("0.3000"),
        annual_rent_amount=Decimal("350000.0000"),
        notes="Khameesiya rental contract",
    )
    touring = TouringAssessment.objects.create(
        contract=contract,
        estimated_total_yield_kg=Decimal("12000.0000"),
        expected_zakat_kg=Decimal("600.0000"),
        expected_institution_share_kg=Decimal("0.0000"),
        committee_members=["عضو 1", "عضو 2", "عضو 3"],
        notes="Touring is assessment only.",
    )
    payment = ContractOperationsService.record_rent_payment(
        contract_id=contract.id,
        amount=Decimal("50000.0000"),
        payment_period="2027-Q1",
        notes="Khameesiya rental settlement",
        user=ctx.users["sector_director"],
    )
    dashboard = ContractOperationsService.build_dashboard(farm_id=ctx.farm.id)
    return {
        "contract_id": contract.id,
        "touring_id": touring.id,
        "rent_status": payment["status"],
        "dashboard_rows": len(dashboard["results"]),
    }


def _attachment_phase(ctx: KhameesiyaContext) -> dict:
    _set_mode(ctx, mode=FarmSettings.MODE_SIMPLE)
    operational_attachment = _safe_attachment(
        farm=ctx.farm,
        uploaded_by=ctx.users["field_operator"],
        related_document_type="daily_log",
        document_scope="khameesiya-operational",
        evidence_class=Attachment.EVIDENCE_CLASS_OPERATIONAL,
    )
    AttachmentPolicyService.scan_attachment(
        attachment=operational_attachment,
        farm_settings=ctx.settings,
    )
    _set_mode(ctx, mode=FarmSettings.MODE_STRICT)
    authoritative_attachment = _safe_attachment(
        farm=ctx.farm,
        uploaded_by=ctx.users["farm_finance_manager"],
        related_document_type="supplier_settlement",
        document_scope="khameesiya-archive",
    )
    AttachmentPolicyService.scan_attachment(
        attachment=authoritative_attachment,
        farm_settings=ctx.settings,
    )
    AttachmentPolicyService.mark_authoritative_after_approval(
        attachment=authoritative_attachment,
        farm_settings=ctx.settings,
        approved_at=timezone.now(),
    )
    AttachmentPolicyService.move_to_archive(attachment=authoritative_attachment)
    suspicious_attachment = _bad_attachment(
        farm=ctx.farm,
        uploaded_by=ctx.users["farm_finance_manager"],
        related_document_type="supplier_settlement",
        document_scope="khameesiya-quarantine",
    )
    AttachmentPolicyService.scan_attachment(
        attachment=suspicious_attachment,
        farm_settings=ctx.settings,
    )
    return {
        "operational_scan_state": operational_attachment.scan_state,
        "authoritative_archive_state": authoritative_attachment.archive_state,
        "quarantine_state": suspicious_attachment.quarantine_state,
    }


def _governance_phase(ctx: KhameesiyaContext) -> dict:
    contract = SharecroppingContract.objects.filter(
        farm=ctx.farm,
        deleted_at__isnull=True,
    ).first()
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
    req.refresh_from_db()
    workbench = ApprovalGovernanceService.role_workbench_snapshot()
    return {
        "approval_request_id": req.id,
        "approval_status": req.status,
        "stage_events": ApprovalStageEvent.objects.filter(request=req).count(),
        "workbench_rows": len(workbench["rows"]),
        "final_required_role": req.final_required_role,
    }


def _run_phase(name: str, category: str, fn, ctx: KhameesiyaContext):
    started_at = timezone.now()
    try:
        result = fn(ctx)
        ended_at = timezone.now()
        return {
            "name": name,
            "category": category,
            "status": "PASS",
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_seconds": round((ended_at - started_at).total_seconds(), 2),
            "result": result,
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
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }


def _build_report(*, phases: list[dict]) -> dict:
    failures = [phase for phase in phases if phase["status"] != "PASS"]
    passed = len(phases) - len(failures)
    strict_summary_score = round((passed / max(len(phases), 1)) * 100, 2)
    return {
        "generated_at": timezone.now().isoformat(),
        "farm_name": KHAMEESIYA_FARM_NAME,
        "farm_slug": KHAMEESIYA_FARM_SLUG,
        "overall_status": "PASS" if not failures else "FAIL",
        "strict_summary_score": strict_summary_score,
        "before_scorecard": BEFORE_SCORECARD,
        "phases": phases,
        "summary": {
            "total": len(phases),
            "passed": passed,
            "failed": len(failures),
            "failure_categories": sorted({phase["category"] for phase in failures}),
        },
    }


def _render_markdown(report: dict) -> str:
    lines = [
        "# Khameesiya Dual-Mode UAT",
        "",
        f"- Farm: `{report['farm_name']}` / `{report['farm_slug']}`",
        f"- Generated: `{report['generated_at']}`",
        f"- Overall Status: `{report['overall_status']}`",
        f"- Strict Summary Score: `{report['strict_summary_score']}` / 100",
        "",
        "## Before Execution",
        "",
    ]
    for key, value in BEFORE_SCORECARD.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Phases")
    lines.append("")
    for phase in report["phases"]:
        lines.append(f"### {phase['name']}")
        lines.append(f"- Status: `{phase['status']}`")
        lines.append(f"- Category: `{phase['category']}`")
        if phase["status"] == "PASS":
            lines.append(
                f"- Result: `{json.dumps(phase['result'], ensure_ascii=False, default=_json_default)}`"
            )
        else:
            lines.append(f"- Error: `{phase['error']}`")
        lines.append("")
    return "\n".join(lines)


def run_khameesiya_uat(*, artifact_root: str | Path, clean_seed: bool = False) -> dict:
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "screenshots").mkdir(parents=True, exist_ok=True)

    ctx = seed_khameesiya_uat(clean=clean_seed)
    phase_specs = [
        ("simple_bootstrap_validation", "governance_reference_defect", _simple_bootstrap_phase),
        ("seasonal_tomato_cycle", "service_layer_defect", _create_tomato_cycle),
        ("mango_perennial_cycle", "service_layer_defect", _create_mango_cycle),
        ("banana_perennial_cycle", "service_layer_defect", _create_banana_cycle),
        ("inventory_procurement", "service_layer_defect", _inventory_and_procurement_phase),
        ("simple_posture_only_finance", "governance_reference_defect", _simple_posture_phase),
        ("strict_mode_transition", "api_contract_defect", _strict_transition_phase),
        ("strict_finance_execution", "service_layer_defect", _strict_finance_phase),
        ("harvest_and_sales", "service_layer_defect", _harvest_sales_phase),
        ("contract_operations", "governance_reference_defect", _contract_operations_phase),
        ("attachments_and_evidence", "api_contract_defect", _attachment_phase),
        ("governance_workbench", "governance_reference_defect", _governance_phase),
    ]
    phases = [_run_phase(name, category, fn, ctx) for name, category, fn in phase_specs]
    report = _build_report(phases=phases)
    _write_json(root / "before_report.json", BEFORE_SCORECARD)
    (root / "before_report.md").write_text(
        "\n".join(
            ["# Khameesiya Before Report", ""]
            + [f"- {key}: `{value}`" for key, value in BEFORE_SCORECARD.items()]
        ),
        encoding="utf-8",
    )
    _write_json(root / "summary.json", report)
    (root / "summary.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


__all__ = [
    "KHAMEESIYA_DEFAULT_PASSWORD",
    "KHAMEESIYA_FARM_NAME",
    "KHAMEESIYA_FARM_SLUG",
    "run_khameesiya_uat",
    "seed_khameesiya_uat",
]
