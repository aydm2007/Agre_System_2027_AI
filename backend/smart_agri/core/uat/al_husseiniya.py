from __future__ import annotations

import json
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, fields
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.postgres.fields.ranges import DateRange
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

import smart_agri.core.uat.khameesiya as kh
from smart_agri.core.models.activity import ActivityEmployee, ActivityItem, ActivityLocation
from smart_agri.core.models.crop import CropProduct, CropVariety
from smart_agri.core.models.custody import CustodyTransfer
from smart_agri.core.models.farm import Farm, Location, LocationIrrigationPolicy
from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.planning import CropPlanLocation
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.models.tree import LocationTreeStock, TreeServiceCoverage
from smart_agri.core.services.custody_transfer_service import CustodyTransferService
from smart_agri.core.services.log_approval_service import LogApprovalService
from smart_agri.core.services.smart_card_stack_service import build_smart_card_stack
from smart_agri.core.services.variance import compute_log_variance
from smart_agri.core.models.report import AsyncReportRequest
from smart_agri.inventory.models import ItemInventory

AL_HUSSEINIYA_FARM_NAME = "الحسينية"
AL_HUSSEINIYA_FARM_SLUG = "al-husseiniya"
AL_HUSSEINIYA_DEFAULT_PASSWORD = "AlHusseiniyaUAT#2026"
ZERO = Decimal("0.0000")

BEFORE_SCORECARD = {
    "canonical_axes": 100,
    "official_al_husseiniya_pack": 0,
    "medium_farm_governance": 0,
    "simple_operational_cycle": 0,
    "perennial_multilocation_service": 0,
    "strict_finance_cycle": 0,
    "reports_and_exports": 0,
    "evidence_artifacts": 0,
}


@dataclass(slots=True)
class AlHusseiniyaContext(kh.KhameesiyaContext):
    pass


@contextmanager
def _patched_identity():
    previous_name = kh.KHAMEESIYA_FARM_NAME
    previous_slug = kh.KHAMEESIYA_FARM_SLUG
    previous_password = kh.KHAMEESIYA_DEFAULT_PASSWORD
    kh.KHAMEESIYA_FARM_NAME = AL_HUSSEINIYA_FARM_NAME
    kh.KHAMEESIYA_FARM_SLUG = AL_HUSSEINIYA_FARM_SLUG
    kh.KHAMEESIYA_DEFAULT_PASSWORD = AL_HUSSEINIYA_DEFAULT_PASSWORD
    try:
        yield
    finally:
        kh.KHAMEESIYA_FARM_NAME = previous_name
        kh.KHAMEESIYA_FARM_SLUG = previous_slug
        kh.KHAMEESIYA_DEFAULT_PASSWORD = previous_password


def _client_for(ctx: AlHusseiniyaContext, user_key: str) -> APIClient:
    client = APIClient()
    client.defaults["HTTP_HOST"] = "localhost"
    client.force_authenticate(user=ctx.users[user_key])
    return client


def _submit_and_approve(ctx: AlHusseiniyaContext, log: DailyLog, approver_key: str = "farm_manager") -> DailyLog:
    submitter = log.created_by or ctx.users["field_operator"]
    approver = ctx.users[approver_key]
    submitted = LogApprovalService.submit_log(submitter, log.id)
    variance = compute_log_variance(submitted)
    if variance["status"] == "WARNING":
        LogApprovalService.note_warning(approver, log.id, note="Al Husseiniya UAT warning reviewed.")
    elif variance["status"] == "CRITICAL":
        LogApprovalService.approve_variance(approver, log.id, note="Al Husseiniya UAT critical variance approved.")
    return LogApprovalService.approve_log(approver, log.id)


def _rename_seed_labels(ctx: AlHusseiniyaContext) -> None:
    ctx.farm.name = AL_HUSSEINIYA_FARM_NAME
    ctx.farm.slug = AL_HUSSEINIYA_FARM_SLUG
    ctx.farm.region = "الحديدة"
    ctx.farm.area = Decimal("245.00")
    ctx.farm.description = "حزمة UAT رسمية لمزرعة الحسينية بمود SIMPLE ثم STRICT ضمن بيئة GRP هجينة."
    ctx.farm.save(update_fields=["name", "slug", "region", "area", "description"])

    ctx.governance.tier = Farm.TIER_MEDIUM
    ctx.governance.rationale = "Al Husseiniya official UAT medium-farm governance."
    ctx.governance.save(update_fields=["tier", "rationale"])

    ctx.cost_center.name = "الحسينية - تشغيل UAT"
    ctx.cost_center.save(update_fields=["name"])

    ctx.assets["tractor"].name = "جرار الحسينية"
    ctx.assets["solar_pump"].name = "مضخة الحسينية"
    ctx.assets["fuel_tank"].name = "خزان وقود الحسينية"
    ctx.assets["packing_line"].name = "خط تعبئة الحسينية"
    for asset in ctx.assets.values():
        asset.save(update_fields=["name"])


def _ensure_multilocation_perennial_seed(ctx: AlHusseiniyaContext) -> None:
    west_orchard, _ = Location.objects.update_or_create(
        farm=ctx.farm,
        code="HS-MAN-W",
        defaults={"name": "بستان المانجو الغربي - الحسينية", "type": "Orchard"},
    )
    ctx.locations["mango_orchard_west"] = west_orchard
    CropPlanLocation.objects.update_or_create(
        crop_plan=ctx.plans["mango"],
        location=west_orchard,
        defaults={"assigned_area": Decimal("4.50")},
    )
    LocationIrrigationPolicy.objects.update_or_create(
        location=west_orchard,
        valid_daterange=DateRange(date(2026, 1, 1), None, "[)"),
        defaults={
            "zakat_rule": LocationIrrigationPolicy.ZAKAT_WELL_5,
            "approved_by": ctx.users["system_admin"],
            "reason": "Al Husseiniya west orchard irrigation policy",
        },
    )
    mango_variety = CropVariety.objects.get(crop=ctx.crops["mango"], name="تيمور")
    source_stock = LocationTreeStock.objects.get(location=ctx.locations["mango_orchard"], crop_variety=mango_variety)
    LocationTreeStock.objects.update_or_create(
        location=west_orchard,
        crop_variety=mango_variety,
        defaults={
            "current_tree_count": 275,
            "productivity_status": source_stock.productivity_status,
            "source": "al_husseiniya_uat",
            "notes": "West orchard coverage for official UAT pack.",
        },
    )


def _dedupe_crop_products(ctx: AlHusseiniyaContext) -> None:
    for crop_key in ("tomato", "mango", "banana"):
        products = list(
            CropProduct.objects.filter(farm=ctx.farm, crop=ctx.crops[crop_key]).order_by("id")
        )
        if len(products) <= 1:
            continue
        keeper = products[0]
        for product in products[1:]:
            product.hard_delete_forensic()
        if crop_key == "tomato":
            keeper.item = ctx.items["tomato_item"]
        elif crop_key == "mango":
            keeper.item = ctx.items["mango_item"]
        elif crop_key == "banana":
            keeper.item = ctx.items["banana_item"]
        keeper.save(update_fields=["item"])


def _preclean_existing_master_duplicates() -> None:
    farm = Farm.objects.filter(slug=AL_HUSSEINIYA_FARM_SLUG, deleted_at__isnull=True).first()
    if not farm:
        return
    CustodyTransfer.objects.filter(farm=farm).delete()
    for inventory in ItemInventory.objects.filter(farm=farm, location__type="Custody"):
        inventory.hard_delete_forensic()
    crop_ids = list(CropProduct.objects.filter(farm=farm).values_list("crop_id", flat=True).distinct())
    for crop_id in crop_ids:
        products = list(CropProduct.objects.filter(farm=farm, crop_id=crop_id).order_by("id"))
        for product in products[1:]:
            product.hard_delete_forensic()


def seed_al_husseiniya_uat(*, clean: bool = False, verbose: bool = False) -> AlHusseiniyaContext:
    _preclean_existing_master_duplicates()
    with _patched_identity():
        base_ctx = kh.seed_khameesiya_uat(clean=clean, verbose=verbose)
    ctx = AlHusseiniyaContext(
        **{field.name: getattr(base_ctx, field.name) for field in fields(kh.KhameesiyaContext)}
    )
    _rename_seed_labels(ctx)
    _ensure_multilocation_perennial_seed(ctx)
    _dedupe_crop_products(ctx)
    ctx.settings.mode = FarmSettings.MODE_SIMPLE
    ctx.settings.approval_profile = FarmSettings.APPROVAL_PROFILE_STRICT_FINANCE
    ctx.settings.single_finance_officer_allowed = False
    ctx.settings.remote_site = False
    ctx.settings.weekly_remote_review_required = False
    ctx.settings.save()
    return ctx


def _simple_reports_phase(ctx: AlHusseiniyaContext) -> dict:
    kh._set_mode(ctx, mode=FarmSettings.MODE_SIMPLE)
    client = _client_for(ctx, "system_admin")
    common_headers = {"HTTP_X_FARM_ID": str(ctx.farm.id)}
    reports_response = client.get(f"/api/v1/reports/?farm={ctx.farm.id}", secure=True, **common_headers)
    advanced_response = client.get(
        f"/api/v1/advanced-report/?farm={ctx.farm.id}&start=2026-01-01&end=2026-12-31",
        secure=True,
        **common_headers,
    )
    shadow_response = client.get(f"/api/v1/shadow-ledger/summary/?farm={ctx.farm.id}", secure=True, **common_headers)
    export_templates = client.get(
        f"/api/v1/export-templates/?farm_id={ctx.farm.id}&ui_surface=reports_hub",
        **common_headers,
    )
    if reports_response.status_code != 200 or advanced_response.status_code != 200 or shadow_response.status_code != 200:
        raise ValidationError("تعذر تحميل تقارير SIMPLE التشغيلية أو shadow ledger لمزرعة الحسينية.")
    serialized = json.dumps(advanced_response.json(), ensure_ascii=False)
    forbidden_keys = ["exact_amount", "strict_finance_trace", "treasury_trace"]
    template_results = export_templates.json().get("results", []) if export_templates.status_code == 200 else []
    return {
        "reports_status": reports_response.status_code,
        "advanced_report_status": advanced_response.status_code,
        "shadow_ledger_status": shadow_response.status_code,
        "export_templates_status": export_templates.status_code,
        "xlsx_available": any(
            entry.get("export_type") == AsyncReportRequest.EXPORT_TYPE_OPERATIONAL_READINESS
            and AsyncReportRequest.FORMAT_XLSX in entry.get("formats", [])
            for entry in template_results
        ),
        "forbidden_finance_keys": [key for key in forbidden_keys if key in serialized],
    }


def _perennial_multilocation_phase(ctx: AlHusseiniyaContext) -> dict:
    kh._set_mode(ctx, mode=FarmSettings.MODE_SIMPLE)
    mango_variety = CropVariety.objects.get(crop=ctx.crops["mango"], name="تيمور")
    log = DailyLog.objects.create(
        farm=ctx.farm,
        log_date=date(2026, 4, 15),
        created_by=ctx.users["field_operator"],
        updated_by=ctx.users["field_operator"],
    )
    activity = kh._ensure_activity(
        log=log,
        crop_plan=ctx.plans["mango"],
        task=ctx.tasks["mango_service"],
        location=ctx.locations["mango_orchard"],
        created_by=ctx.users["field_operator"],
        crop_variety=mango_variety,
        cost_total=Decimal("215000.0000"),
    )
    ActivityLocation.objects.update_or_create(
        activity=activity,
        location=ctx.locations["mango_orchard_west"],
        defaults={"allocated_percentage": Decimal("45.00")},
    )
    TreeServiceCoverage.objects.update_or_create(
        activity=activity,
        location=ctx.locations["mango_orchard"],
        defaults={
            "farm": ctx.farm,
            "service_type": TreeServiceCoverage.IRRIGATION,
            "target_scope": TreeServiceCoverage.SCOPE_LOCATION,
            "crop_variety": mango_variety,
            "trees_covered": 500,
            "distribution_mode": TreeServiceCoverage.DISTRIBUTION_UNIFORM,
            "distribution_factor": Decimal("1.0000"),
            "date": log.log_date,
            "recorded_by": ctx.users["agronomist"],
        },
    )
    TreeServiceCoverage.objects.update_or_create(
        activity=activity,
        location=ctx.locations["mango_orchard_west"],
        defaults={
            "farm": ctx.farm,
            "service_type": TreeServiceCoverage.IRRIGATION,
            "target_scope": TreeServiceCoverage.SCOPE_LOCATION,
            "crop_variety": mango_variety,
            "trees_covered": 275,
            "distribution_mode": TreeServiceCoverage.DISTRIBUTION_EXCEPTION_WEIGHTED,
            "distribution_factor": Decimal("0.5500"),
            "date": log.log_date,
            "recorded_by": ctx.users["agronomist"],
        },
    )
    _submit_and_approve(ctx, log)
    return {
        "activity_id": activity.id,
        "activity_locations": ActivityLocation.objects.filter(activity=activity).count(),
        "coverage_rows": TreeServiceCoverage.objects.filter(activity=activity).count(),
        "west_orchard_stock": LocationTreeStock.objects.get(
            location=ctx.locations["mango_orchard_west"],
            crop_variety=mango_variety,
        ).current_tree_count,
    }


def _seasonal_tomato_cycle(ctx: AlHusseiniyaContext) -> dict:
    kh._set_mode(ctx, mode=FarmSettings.MODE_SIMPLE)
    transfer = CustodyTransferService.issue_transfer(
        farm=ctx.farm,
        supervisor=ctx.supervisor,
        item=ctx.items["urea"],
        source_location=ctx.locations["central_store"],
        qty="80",
        actor=ctx.users["storekeeper"],
        batch_number="OPEN-UREA",
        idempotency_key=f"{ctx.farm.slug}-tomato-custody-issue-{timezone.now().timestamp()}",
    )
    CustodyTransferService.accept_transfer(transfer=transfer, actor=ctx.users["field_operator"])
    log = DailyLog.objects.create(
        farm=ctx.farm,
        log_date=timezone.localdate() - timedelta(days=3),
        notes="Al Husseiniya tomato cycle",
        created_by=ctx.users["field_operator"],
        updated_by=ctx.users["field_operator"],
        supervisor=ctx.supervisor,
    )
    activity = kh._ensure_activity(
        log=log,
        crop_plan=ctx.plans["tomato"],
        task=ctx.tasks["tomato_service"],
        location=ctx.locations["tomato_field"],
        created_by=ctx.users["field_operator"],
        cost_total=Decimal("1800.0000"),
    )
    activity.asset = ctx.assets["tractor"]
    activity.save(update_fields=["asset"])
    ActivityItem.objects.create(
        activity=activity,
        item=ctx.items["urea"],
        qty=Decimal("55.000"),
        applied_qty=Decimal("55.000"),
        waste_qty=ZERO,
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
    approved_log = _submit_and_approve(ctx, log)
    stack = build_smart_card_stack(activity)
    return {
        "daily_log_id": approved_log.id,
        "activity_id": activity.id,
        "variance_status": approved_log.variance_status,
        "smart_card_keys": [row.get("card_key") for row in stack],
    }


def _strict_reports_phase(ctx: AlHusseiniyaContext) -> dict:
    kh._set_mode(ctx, mode=FarmSettings.MODE_STRICT)
    client = _client_for(ctx, "farm_finance_manager")
    common_headers = {"HTTP_X_FARM_ID": str(ctx.farm.id)}
    trial_balance = client.get(f"/api/v1/finance/trial-balance/?farm={ctx.farm.id}", secure=True, **common_headers)
    profitability = client.get(
        f"/api/v1/finance/profitability-summary/?farm={ctx.farm.id}",
        secure=True,
        **common_headers,
    )
    export_templates = client.get(
        f"/api/v1/export-templates/?farm_id={ctx.farm.id}&ui_surface=reports_hub",
        **common_headers,
    )
    if trial_balance.status_code != 200 or profitability.status_code != 200:
        raise ValidationError("تعذر تحميل trial balance أو profitability summary في STRICT.")
    payload = profitability.json()
    template_results = export_templates.json().get("results", []) if export_templates.status_code == 200 else []
    return {
        "trial_balance_status": trial_balance.status_code,
        "profitability_status": profitability.status_code,
        "strict_export_templates_status": export_templates.status_code,
        "governance_export_available": any(
            entry.get("export_type") == AsyncReportRequest.EXPORT_TYPE_GOVERNANCE_WORK_QUEUE
            and AsyncReportRequest.FORMAT_XLSX in entry.get("formats", [])
            for entry in template_results
        ),
        "profitability_keys": sorted(list(payload.keys()))[:8],
    }


def _run_phase(name: str, category: str, fn, ctx: AlHusseiniyaContext) -> dict:
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
        "farm_name": AL_HUSSEINIYA_FARM_NAME,
        "farm_slug": AL_HUSSEINIYA_FARM_SLUG,
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
        "# Al Husseiniya Dual-Mode UAT",
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
            lines.append(f"- Result: `{json.dumps(phase['result'], ensure_ascii=False, default=kh._json_default)}`")
        else:
            lines.append(f"- Error: `{phase['error']}`")
        lines.append("")
    return "\n".join(lines)


def run_al_husseiniya_uat(*, artifact_root: str | Path, clean_seed: bool = False) -> dict:
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    (root / "screenshots").mkdir(parents=True, exist_ok=True)

    ctx = seed_al_husseiniya_uat(clean=clean_seed)
    phase_specs = [
        ("simple_bootstrap_validation", "governance_reference_defect", kh._simple_bootstrap_phase),
        ("seasonal_tomato_cycle", "service_layer_defect", _seasonal_tomato_cycle),
        ("mango_perennial_multilocation_cycle", "service_layer_defect", _perennial_multilocation_phase),
        ("banana_perennial_cycle", "service_layer_defect", kh._create_banana_cycle),
        ("inventory_procurement_cycle", "service_layer_defect", kh._inventory_and_procurement_phase),
        ("simple_posture_only_finance", "governance_reference_defect", kh._simple_posture_phase),
        ("simple_reports_and_shadow_ledger", "api_contract_defect", _simple_reports_phase),
        ("strict_mode_transition", "api_contract_defect", kh._strict_transition_phase),
        ("strict_finance_execution", "service_layer_defect", kh._strict_finance_phase),
        ("harvest_and_sales", "service_layer_defect", kh._harvest_sales_phase),
        ("contract_operations", "governance_reference_defect", kh._contract_operations_phase),
        ("strict_reports_and_exports", "api_contract_defect", _strict_reports_phase),
        ("attachments_and_evidence", "api_contract_defect", kh._attachment_phase),
        ("governance_workbench", "governance_reference_defect", kh._governance_phase),
    ]
    phases = [_run_phase(name, category, fn, ctx) for name, category, fn in phase_specs]
    report = _build_report(phases=phases)

    kh._write_json(root / "before_report.json", BEFORE_SCORECARD)
    (root / "before_report.md").write_text(
        "\n".join(["# Al Husseiniya Before Report", ""] + [f"- {key}: `{value}`" for key, value in BEFORE_SCORECARD.items()]),
        encoding="utf-8",
    )
    kh._write_json(root / "logs" / "phases.json", {"phases": phases})
    kh._write_json(root / "summary.json", report)
    (root / "summary.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


__all__ = [
    "AL_HUSSEINIYA_DEFAULT_PASSWORD",
    "AL_HUSSEINIYA_FARM_NAME",
    "AL_HUSSEINIYA_FARM_SLUG",
    "run_al_husseiniya_uat",
    "seed_al_husseiniya_uat",
]
