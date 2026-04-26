from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from smart_agri.core.models import Crop, CropPlan, CropPlanBudgetLine, CropPlanLocation, Farm, Location, PlannedActivity, PlanImportLog, Season, Task
from smart_agri.core.services.sensitive_audit import log_sensitive_mutation


@dataclass(frozen=True)
class PlanningRowResult:
    payload: dict
    duplicate_key: str


class PlanningImportService:
    TEMPLATE_MASTER_SCHEDULE = "planning_master_schedule"
    TEMPLATE_CROP_PLAN_STRUCTURE = "planning_crop_plan_structure"
    TEMPLATE_CROP_PLAN_BUDGET = "planning_crop_plan_budget"

    @classmethod
    def build_template_rows(cls, *, template_code: str, farm: Farm, crop_plan_id=None):
        if template_code == cls.TEMPLATE_MASTER_SCHEDULE:
            season = Season.objects.filter(is_active=True).order_by("-start_date").first()
            crop = Crop.objects.filter(deleted_at__isnull=True).order_by("name").first()
            location = Location.objects.filter(farm=farm, deleted_at__isnull=True).order_by("name").first()
            return [[
                "خطة تشغيل موسمية",
                season.name if season else str(timezone.localdate().year),
                crop.name if crop else "",
                location.name if location else "",
                timezone.localdate().isoformat(),
                timezone.localdate().isoformat(),
                "0",
                "YER",
                "",
            ]]
        crop_plan = cls._resolve_crop_plan_for_farm(farm=farm, crop_plan_id=crop_plan_id, required=True)
        if template_code == cls.TEMPLATE_CROP_PLAN_STRUCTURE:
            tasks = Task.objects.filter(crop=crop_plan.crop, deleted_at__isnull=True).order_by("stage", "name")[:50]
            rows = [
                [
                    task.id,
                    task.name,
                    crop_plan.start_date.isoformat() if crop_plan.start_date else "",
                    str(task.estimated_hours or Decimal("0")),
                    task.stage or "",
                    "",
                ]
                for task in tasks
            ]
            return rows or [["", "", crop_plan.start_date.isoformat() if crop_plan.start_date else "", "", "", ""]]
        if template_code == cls.TEMPLATE_CROP_PLAN_BUDGET:
            existing_lines = {
                (line.task_id, line.category): line
                for line in CropPlanBudgetLine.objects.filter(crop_plan=crop_plan, deleted_at__isnull=True).select_related("task")
            }
            tasks = Task.objects.filter(crop=crop_plan.crop, deleted_at__isnull=True).order_by("stage", "name")[:50]
            rows = []
            for task in tasks:
                line = existing_lines.get((task.id, CropPlanBudgetLine.CATEGORY_MATERIALS))
                rows.append(
                    [
                        task.id,
                        task.name,
                        (line.category if line else CropPlanBudgetLine.CATEGORY_MATERIALS),
                        str(line.qty_budget if line and line.qty_budget is not None else ""),
                        line.uom if line else "",
                        str(line.rate_budget if line else ""),
                        str(line.total_budget if line else ""),
                        line.currency if line else (crop_plan.currency or "YER"),
                    ]
                )
            return rows or [["", "", CropPlanBudgetLine.CATEGORY_MATERIALS, "", "", "", "", crop_plan.currency or "YER"]]
        raise ValidationError("Unsupported planning template.")

    @classmethod
    def normalize_row(cls, *, template_code: str, farm: Farm, row: dict, job_metadata: dict | None = None) -> PlanningRowResult:
        metadata = job_metadata or {}
        if template_code == cls.TEMPLATE_MASTER_SCHEDULE:
            return cls._normalize_master_schedule_row(farm=farm, row=row)
        if template_code == cls.TEMPLATE_CROP_PLAN_STRUCTURE:
            crop_plan = cls._resolve_crop_plan_for_farm(
                farm=farm,
                crop_plan_id=metadata.get("crop_plan_id"),
                required=True,
            )
            return cls._normalize_structure_row(farm=farm, crop_plan=crop_plan, row=row)
        if template_code == cls.TEMPLATE_CROP_PLAN_BUDGET:
            crop_plan = cls._resolve_crop_plan_for_farm(
                farm=farm,
                crop_plan_id=metadata.get("crop_plan_id"),
                required=True,
            )
            return cls._normalize_budget_row(farm=farm, crop_plan=crop_plan, row=row)
        raise ValidationError("Unsupported planning template.")

    @classmethod
    @transaction.atomic
    def apply_row(cls, *, actor, template_code: str, farm: Farm, row: dict, job_id: int, job_metadata: dict | None = None):
        metadata = job_metadata or {}
        if template_code == cls.TEMPLATE_MASTER_SCHEDULE:
            return cls._apply_master_schedule_row(actor=actor, farm=farm, row=row, job_id=job_id)
        if template_code == cls.TEMPLATE_CROP_PLAN_STRUCTURE:
            crop_plan = cls._resolve_crop_plan_for_farm(
                farm=farm,
                crop_plan_id=metadata.get("crop_plan_id"),
                required=True,
            )
            return cls._apply_structure_row(actor=actor, farm=farm, crop_plan=crop_plan, row=row, job_id=job_id)
        if template_code == cls.TEMPLATE_CROP_PLAN_BUDGET:
            crop_plan = cls._resolve_crop_plan_for_farm(
                farm=farm,
                crop_plan_id=metadata.get("crop_plan_id"),
                required=True,
            )
            return cls._apply_budget_row(actor=actor, farm=farm, crop_plan=crop_plan, row=row, job_id=job_id)
        raise ValidationError("Unsupported planning template.")

    @classmethod
    def _normalize_master_schedule_row(cls, *, farm: Farm, row: dict) -> PlanningRowResult:
        plan_name = str(row.get("اسم_الخطة") or "").strip()
        if not plan_name:
            raise ValidationError("اسم الخطة مطلوب.")
        crop = cls._resolve_crop(farm=farm, value=row.get("المحصول"))
        season = cls._resolve_season(row.get("الموسم"))
        location = cls._resolve_location(farm=farm, value=row.get("الموقع"), required=False)
        start_date = cls._parse_date(row.get("من"), field_name="من")
        end_date = cls._parse_date(row.get("إلى"), field_name="إلى")
        if start_date > end_date:
            raise ValidationError("تاريخ البداية يجب أن يسبق تاريخ النهاية.")
        area = cls._parse_decimal(row.get("المساحة"), field_name="المساحة", allow_blank=True) or Decimal("0")
        currency = str(row.get("العملة") or "YER").strip() or "YER"
        note = str(row.get("ملاحظات") or "").strip()
        duplicate_key = f"master:{plan_name}:{crop.id}:{season.id}:{start_date.isoformat()}:{end_date.isoformat()}"
        return PlanningRowResult(
            payload={
                "plan_name": plan_name,
                "crop_id": crop.id,
                "crop_name": crop.name,
                "season_id": season.id,
                "season_name": season.name,
                "location_id": location.id if location else None,
                "location_name": location.name if location else "",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "area": str(area),
                "currency": currency,
                "note": note,
            },
            duplicate_key=duplicate_key,
        )

    @classmethod
    def _normalize_structure_row(cls, *, farm: Farm, crop_plan: CropPlan, row: dict) -> PlanningRowResult:
        task = cls._resolve_task(crop_plan=crop_plan, value=row.get("رقم_النشاط"), fallback_name=row.get("اسم_النشاط"))
        planned_date = cls._parse_date(row.get("التاريخ"), field_name="التاريخ")
        hours = cls._parse_decimal(row.get("الساعات"), field_name="الساعات", allow_blank=True) or Decimal("0")
        if hours < 0:
            raise ValidationError("الساعات يجب أن تكون غير سالبة.")
        stage = str(row.get("المرحلة") or "").strip()
        note = str(row.get("ملاحظات") or "").strip()
        duplicate_key = f"struct:{crop_plan.id}:{task.id}:{planned_date.isoformat()}"
        return PlanningRowResult(
            payload={
                "crop_plan_id": crop_plan.id,
                "crop_plan_name": crop_plan.name,
                "task_id": task.id,
                "task_name": task.name,
                "planned_date": planned_date.isoformat(),
                "estimated_hours": str(hours),
                "stage": stage,
                "note": note,
            },
            duplicate_key=duplicate_key,
        )

    @classmethod
    def _normalize_budget_row(cls, *, farm: Farm, crop_plan: CropPlan, row: dict) -> PlanningRowResult:
        task = cls._resolve_task(crop_plan=crop_plan, value=row.get("رقم_النشاط"), fallback_name=row.get("اسم_النشاط"))
        category = str(row.get("فئة_الميزانية") or CropPlanBudgetLine.CATEGORY_OTHER).strip().lower()
        if category not in {choice[0] for choice in CropPlanBudgetLine.CATEGORY_CHOICES}:
            raise ValidationError("فئة الميزانية غير معتمدة.")
        qty_budget = cls._parse_decimal(row.get("الكمية"), field_name="الكمية", allow_blank=True)
        rate_budget = cls._parse_decimal(row.get("السعر"), field_name="السعر", allow_blank=True) or Decimal("0")
        total_budget = cls._parse_decimal(row.get("الإجمالي"), field_name="الإجمالي", allow_blank=True)
        if total_budget is None:
            total_budget = (qty_budget or Decimal("0")) * rate_budget
        if total_budget < 0:
            raise ValidationError("إجمالي الميزانية يجب أن يكون غير سالب.")
        uom = str(row.get("الوحدة") or "").strip()
        currency = str(row.get("العملة") or crop_plan.currency or "YER").strip() or (crop_plan.currency or "YER")
        duplicate_key = f"budget:{crop_plan.id}:{task.id}:{category}"
        return PlanningRowResult(
            payload={
                "crop_plan_id": crop_plan.id,
                "crop_plan_name": crop_plan.name,
                "task_id": task.id,
                "task_name": task.name,
                "category": category,
                "qty_budget": str(qty_budget) if qty_budget is not None else "",
                "uom": uom,
                "rate_budget": str(rate_budget),
                "total_budget": str(total_budget),
                "currency": currency,
            },
            duplicate_key=duplicate_key,
        )

    @classmethod
    def _apply_master_schedule_row(cls, *, actor, farm: Farm, row: dict, job_id: int):
        crop = Crop.objects.get(pk=row["crop_id"])
        season = Season.objects.get(pk=row["season_id"])
        defaults = {
            "season": season,
            "currency": row["currency"],
            "area": Decimal(str(row["area"] or "0")),
            "notes": row.get("note") or "",
            "created_by": actor,
            "updated_by": actor,
        }
        plan, created = CropPlan.objects.get_or_create(
            farm=farm,
            crop=crop,
            name=row["plan_name"],
            start_date=cls._parse_date(row["start_date"], field_name="start_date"),
            end_date=cls._parse_date(row["end_date"], field_name="end_date"),
            defaults=defaults,
        )
        if not created:
            changed = False
            for field, value in defaults.items():
                if field == "created_by":
                    continue
                if getattr(plan, field) != value:
                    setattr(plan, field, value)
                    changed = True
            if changed:
                plan.save()
        if row.get("location_id"):
            location = Location.objects.get(pk=row["location_id"], farm=farm)
            CropPlanLocation.objects.update_or_create(
                crop_plan=plan,
                location=location,
                defaults={"assigned_area": Decimal(str(row["area"] or "0"))},
            )
        cls._log_plan_import(
            crop_plan=plan,
            actor=actor,
            job_id=job_id,
            summary={"template_code": cls.TEMPLATE_MASTER_SCHEDULE, "created": created},
        )
        log_sensitive_mutation(
            actor=actor,
            action="planning_master_schedule_upsert",
            model_name="CropPlan",
            object_id=plan.pk,
            reason="planning_import",
            old_value=None,
            new_value={"name": plan.name, "season": plan.season_id, "currency": plan.currency},
            farm_id=farm.id,
            context={"job_id": job_id, "created": created},
        )
        return plan

    @classmethod
    def _apply_structure_row(cls, *, actor, farm: Farm, crop_plan: CropPlan, row: dict, job_id: int):
        task = Task.objects.get(pk=row["task_id"])
        planned_activity, created = PlannedActivity.objects.get_or_create(
            crop_plan=crop_plan,
            task=task,
            planned_date=cls._parse_date(row["planned_date"], field_name="planned_date"),
            defaults={
                "estimated_hours": Decimal(str(row["estimated_hours"] or "0")),
                "notes": row.get("note") or "",
            },
        )
        if not created:
            planned_activity.estimated_hours = Decimal(str(row["estimated_hours"] or "0"))
            planned_activity.notes = row.get("note") or ""
            planned_activity.save(update_fields=["estimated_hours", "notes", "updated_at"])
        cls._log_plan_import(
            crop_plan=crop_plan,
            actor=actor,
            job_id=job_id,
            summary={"template_code": cls.TEMPLATE_CROP_PLAN_STRUCTURE, "task_id": task.id, "created": created},
        )
        log_sensitive_mutation(
            actor=actor,
            action="planning_structure_upsert",
            model_name="PlannedActivity",
            object_id=planned_activity.pk,
            reason="planning_import",
            old_value=None,
            new_value={"task_id": task.id, "planned_date": row["planned_date"]},
            farm_id=farm.id,
            context={"job_id": job_id, "crop_plan_id": crop_plan.id, "created": created},
        )
        return planned_activity

    @classmethod
    def _apply_budget_row(cls, *, actor, farm: Farm, crop_plan: CropPlan, row: dict, job_id: int):
        task = Task.objects.get(pk=row["task_id"])
        defaults = {
            "qty_budget": Decimal(str(row["qty_budget"] or "0")) if str(row.get("qty_budget") or "").strip() else None,
            "uom": row.get("uom") or "",
            "rate_budget": Decimal(str(row["rate_budget"] or "0")),
            "total_budget": Decimal(str(row["total_budget"] or "0")),
            "currency": row.get("currency") or crop_plan.currency or "YER",
        }
        budget_line, created = CropPlanBudgetLine.objects.update_or_create(
            crop_plan=crop_plan,
            task=task,
            category=row["category"],
            defaults=defaults,
        )
        cls._recalculate_budget_totals(crop_plan)
        cls._log_plan_import(
            crop_plan=crop_plan,
            actor=actor,
            job_id=job_id,
            summary={"template_code": cls.TEMPLATE_CROP_PLAN_BUDGET, "task_id": task.id, "created": created},
        )
        log_sensitive_mutation(
            actor=actor,
            action="planning_budget_upsert",
            model_name="CropPlanBudgetLine",
            object_id=budget_line.pk,
            reason="planning_import",
            old_value=None,
            new_value={"task_id": task.id, "category": row["category"], "total_budget": row["total_budget"]},
            farm_id=farm.id,
            context={"job_id": job_id, "crop_plan_id": crop_plan.id, "created": created},
        )
        return budget_line

    @classmethod
    def _recalculate_budget_totals(cls, crop_plan: CropPlan):
        lines = CropPlanBudgetLine.objects.filter(crop_plan=crop_plan, deleted_at__isnull=True)
        totals = {
            CropPlanBudgetLine.CATEGORY_MATERIALS: Decimal("0"),
            CropPlanBudgetLine.CATEGORY_LABOR: Decimal("0"),
            CropPlanBudgetLine.CATEGORY_MACHINERY: Decimal("0"),
            CropPlanBudgetLine.CATEGORY_OTHER: Decimal("0"),
        }
        for line in lines:
            totals[line.category] = totals.get(line.category, Decimal("0")) + Decimal(str(line.total_budget or "0"))
        crop_plan.budget_materials = totals[CropPlanBudgetLine.CATEGORY_MATERIALS]
        crop_plan.budget_labor = totals[CropPlanBudgetLine.CATEGORY_LABOR]
        crop_plan.budget_machinery = totals[CropPlanBudgetLine.CATEGORY_MACHINERY]
        crop_plan.budget_total = sum(totals.values(), Decimal("0"))
        crop_plan.budget_amount = crop_plan.budget_total
        crop_plan.save(update_fields=["budget_materials", "budget_labor", "budget_machinery", "budget_total", "budget_amount", "updated_at"])

    @classmethod
    def _resolve_crop(cls, *, farm: Farm, value):
        name = str(value or "").strip()
        if not name:
            raise ValidationError("المحصول مطلوب.")
        crop = Crop.objects.filter(name__iexact=name, deleted_at__isnull=True).first()
        if crop is None:
            raise ValidationError(f"المحصول غير معروف: {name}")
        return crop

    @classmethod
    def _resolve_location(cls, *, farm: Farm, value, required=False):
        name = str(value or "").strip()
        if not name:
            if required:
                raise ValidationError("الموقع مطلوب.")
            return None
        location = Location.objects.filter(farm=farm, name__iexact=name, deleted_at__isnull=True).first()
        if location is None:
            raise ValidationError(f"الموقع غير معروف: {name}")
        return location

    @classmethod
    def _resolve_task(cls, *, crop_plan: CropPlan, value, fallback_name=None):
        if str(value or "").strip():
            try:
                task = Task.objects.get(pk=int(value), crop=crop_plan.crop, deleted_at__isnull=True)
                return task
            except (ValueError, Task.DoesNotExist):
                raise ValidationError(f"رقم النشاط غير معروف داخل المحصول الحالي: {value}")
        name = str(fallback_name or "").strip()
        if not name:
            raise ValidationError("رقم النشاط أو اسم النشاط مطلوب.")
        task = Task.objects.filter(crop=crop_plan.crop, name__iexact=name, deleted_at__isnull=True).first()
        if task is None:
            raise ValidationError(f"اسم النشاط غير معروف داخل المحصول الحالي: {name}")
        return task

    @classmethod
    def _resolve_season(cls, value):
        season_name = str(value or "").strip()
        if not season_name:
            raise ValidationError("الموسم مطلوب.")
        season = Season.objects.filter(name__iexact=season_name).first()
        if season is not None:
            return season
        try:
            year = int(season_name)
        except ValueError:
            year = timezone.localdate().year
        return Season.objects.create(
            name=season_name,
            start_date=date(year, 1, 1),
            end_date=date(year, 12, 31),
            is_active=True,
        )

    @classmethod
    def _resolve_crop_plan_for_farm(cls, *, farm: Farm, crop_plan_id, required=False):
        if crop_plan_id in (None, "", 0, "0"):
            if required:
                raise ValidationError("القالب يتطلب تحديد خطة زراعية مستهدفة.")
            return None
        crop_plan = CropPlan.objects.filter(pk=crop_plan_id, farm=farm, deleted_at__isnull=True).first()
        if crop_plan is None and required:
            raise ValidationError("الخطة الزراعية المستهدفة غير موجودة ضمن هذه المزرعة.")
        return crop_plan

    @staticmethod
    def _parse_date(value, *, field_name: str):
        if isinstance(value, date):
            return value
        raw = str(value or "").strip()
        if not raw:
            raise ValidationError(f"{field_name} مطلوب.")
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise ValidationError(f"{field_name} يجب أن يكون بصيغة YYYY-MM-DD.") from exc

    @staticmethod
    def _parse_decimal(value, *, field_name: str, allow_blank=False):
        raw = str(value or "").strip()
        if not raw:
            if allow_blank:
                return None
            raise ValidationError(f"{field_name} مطلوب.")
        try:
            return Decimal(raw)
        except (InvalidOperation, TypeError) as exc:
            raise ValidationError(f"{field_name} يجب أن يكون رقمًا عشريًا صالحًا.") from exc

    @staticmethod
    def _log_plan_import(*, crop_plan: CropPlan, actor, job_id: int, summary: dict):
        PlanImportLog.objects.create(
            crop_plan=crop_plan,
            created_by=actor,
            status=PlanImportLog.STATUS_SUCCESS,
            summary={**summary, "job_id": job_id},
            file_name=f"async-import-job-{job_id}.xlsx",
            imported_count=1,
            skipped_count=0,
            dry_run=False,
        )
