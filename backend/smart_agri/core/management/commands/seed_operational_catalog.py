from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from smart_agri.core.models import (
    Activity,
    ActivityCostSnapshot,
    ActivityItem,
    Crop,
    CropMaterial,
    CropPlan,
    CropPlanBudgetLine,
    CropProduct,
    CropTemplate,
    CropTemplateTask,
    DailyLog,
    Farm,
    FarmCrop,
    Location,
    PlannedActivity,
    PlannedMaterial,
    Season,
    Task,
)
from smart_agri.inventory.models import Item


@dataclass(frozen=True)
class TaskBlueprint:
    stage: str
    name: str
    requires_area: bool = False
    requires_machinery: bool = False
    requires_well: bool = False
    is_harvest_task: bool = False
    requires_tree_count: bool = False
    is_perennial_procedure: bool = False
    is_asset_task: bool = False
    asset_type: str = ""
    target_asset_type: str = "NONE"


class Command(BaseCommand):
    help = "Seed reproducible operational crop catalog/plans for active farms."

    TARGET_CROPS = {
        "مانجو": {
            "is_perennial": True,
            "mode": "Open",
            "varieties": ["قلب الثور", "التيمور", "السوداني", "الزبدة"],
        },
        "موز": {
            "is_perennial": True,
            "mode": "Open",
            "varieties": ["موز درجة اولى"],
        },
        "قمح": {"is_perennial": False, "mode": "Open", "varieties": []},
        "ذرة صفراء": {"is_perennial": False, "mode": "Open", "varieties": []},
        "ذرة بيضاء": {"is_perennial": False, "mode": "Open", "varieties": []},
    }

    TASKS = {
        "مانجو": [
            TaskBlueprint("إعداد", "تقليم أشجار المانجو", requires_tree_count=True, is_perennial_procedure=True, target_asset_type="TREE"),
            TaskBlueprint("رعاية", "ري المانجو", requires_well=True, is_asset_task=True, asset_type="WELL", target_asset_type="WELL"),
            TaskBlueprint("رعاية", "تسميد المانجو", requires_tree_count=True, is_perennial_procedure=True, target_asset_type="TREE"),
            TaskBlueprint("وقاية", "مكافحة آفات المانجو", requires_area=True, target_asset_type="SECTOR"),
            TaskBlueprint("حصاد", "حصاد المانجو", is_harvest_task=True, requires_tree_count=True, target_asset_type="TREE"),
        ],
        "موز": [
            TaskBlueprint("إعداد", "تجهيز جور الموز", requires_area=True, target_asset_type="SECTOR"),
            TaskBlueprint("رعاية", "خدمة فسائل الموز", requires_tree_count=True, is_perennial_procedure=True, target_asset_type="TREE"),
            TaskBlueprint("ري", "ري الموز", requires_well=True, is_asset_task=True, asset_type="WELL", target_asset_type="WELL"),
            TaskBlueprint("تسميد", "تسميد الموز", requires_tree_count=True, target_asset_type="TREE"),
            TaskBlueprint("حصاد", "حصاد الموز", is_harvest_task=True, requires_tree_count=True, target_asset_type="TREE"),
        ],
        "قمح": [
            TaskBlueprint("إعداد", "تحضير أرض القمح", requires_area=True, requires_machinery=True, is_asset_task=True, asset_type="MACHINE", target_asset_type="MACHINE"),
            TaskBlueprint("زراعة", "بذر القمح", requires_area=True, target_asset_type="SECTOR"),
            TaskBlueprint("خدمة", "تسميد القمح", requires_area=True, target_asset_type="SECTOR"),
            TaskBlueprint("ري", "ري القمح", requires_well=True, target_asset_type="WELL"),
            TaskBlueprint("حصاد", "حصاد القمح", is_harvest_task=True, requires_machinery=True, target_asset_type="MACHINE"),
        ],
        "ذرة صفراء": [
            TaskBlueprint("إعداد", "تحضير أرض الذرة الصفراء", requires_area=True, requires_machinery=True, target_asset_type="MACHINE"),
            TaskBlueprint("زراعة", "زراعة الذرة الصفراء", requires_area=True, target_asset_type="SECTOR"),
            TaskBlueprint("خدمة", "تسميد الذرة الصفراء", requires_area=True, target_asset_type="SECTOR"),
            TaskBlueprint("ري", "ري الذرة الصفراء", requires_well=True, target_asset_type="WELL"),
            TaskBlueprint("حصاد", "حصاد الذرة الصفراء", is_harvest_task=True, requires_machinery=True, target_asset_type="MACHINE"),
        ],
        "ذرة بيضاء": [
            TaskBlueprint("إعداد", "تحضير أرض الذرة البيضاء", requires_area=True, requires_machinery=True, target_asset_type="MACHINE"),
            TaskBlueprint("زراعة", "زراعة الذرة البيضاء", requires_area=True, target_asset_type="SECTOR"),
            TaskBlueprint("خدمة", "تسميد الذرة البيضاء", requires_area=True, target_asset_type="SECTOR"),
            TaskBlueprint("ري", "ري الذرة البيضاء", requires_well=True, target_asset_type="WELL"),
            TaskBlueprint("حصاد", "حصاد الذرة البيضاء", is_harvest_task=True, requires_machinery=True, target_asset_type="MACHINE"),
        ],
    }

    PRODUCTS = {
        "مانجو": "مانجو طازج",
        "موز": "موز طازج",
        "قمح": "حبوب القمح",
        "ذرة صفراء": "حبوب ذرة صفراء",
        "ذرة بيضاء": "حبوب ذرة بيضاء",
    }

    MATERIALS = {
        "مانجو": [("سماد عضوي", "Input", "kg", Decimal("180")), ("سماد مركب", "Input", "kg", Decimal("120")), ("مبيد حشري", "Input", "L", Decimal("12"))],
        "موز": [("سماد عضوي", "Input", "kg", Decimal("220")), ("سماد بوتاسي", "Input", "kg", Decimal("90")), ("مبيد فطري", "Input", "L", Decimal("10"))],
        "قمح": [("بذور القمح", "Seed", "kg", Decimal("250")), ("سماد يوريا", "Input", "kg", Decimal("140")), ("ديزل زراعي", "Fuel", "L", Decimal("90"))],
        "ذرة صفراء": [("بذور ذرة صفراء", "Seed", "kg", Decimal("80")), ("سماد نيتروجيني", "Input", "kg", Decimal("110")), ("ديزل زراعي", "Fuel", "L", Decimal("75"))],
        "ذرة بيضاء": [("بذور ذرة بيضاء", "Seed", "kg", Decimal("80")), ("سماد نيتروجيني", "Input", "kg", Decimal("110")), ("ديزل زراعي", "Fuel", "L", Decimal("75"))],
    }

    def add_arguments(self, parser):
        parser.add_argument("--season", type=int, default=timezone.localdate().year)
        parser.add_argument("--clean-ops", dest="clean_ops", action="store_true")
        parser.add_argument("--no-clean-ops", dest="clean_ops", action="store_false")
        parser.set_defaults(clean_ops=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        season_year = int(options["season"])
        clean_ops = bool(options["clean_ops"])
        dry_run = bool(options["dry_run"])

        with transaction.atomic():
            report = {
                "cleanup": {},
                "created": {
                    "tasks": 0,
                    "templates": 0,
                    "template_tasks": 0,
                    "products": 0,
                    "materials": 0,
                    "plans": 0,
                    "planned_activities": 0,
                    "planned_materials": 0,
                    "budget_lines": 0,
                },
            }

            target_names = set(self.TARGET_CROPS.keys())
            crops = self._upsert_crops_and_varieties(target_names)

            if clean_ops:
                report["cleanup"] = self._soft_cleanup(target_names)

            season = self._ensure_season(season_year)
            supported_tasks_table_exists = "core_crop_supported_tasks" in connection.introspection.table_names()

            self._rebuild_catalog(crops, report, supported_tasks_table_exists)
            self._rebuild_plans(crops, season, report)

            self._print_report(season_year, clean_ops, dry_run, supported_tasks_table_exists, report)

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry-run completed. Transaction rolled back."))

    def _upsert_crops_and_varieties(self, target_names):
        now = timezone.now()
        crops = {}
        for crop_name, conf in self.TARGET_CROPS.items():
            crop, _ = Crop.objects.get_or_create(
                name=crop_name,
                mode=conf["mode"],
                defaults={"is_perennial": conf["is_perennial"], "is_active": True, "deleted_at": None},
            )
            changed = False
            if crop.is_perennial != conf["is_perennial"]:
                crop.is_perennial = conf["is_perennial"]
                changed = True
            if not crop.is_active:
                crop.is_active = True
                changed = True
            if crop.deleted_at is not None:
                crop.deleted_at = None
                changed = True
            if changed:
                crop.save(update_fields=["is_perennial", "is_active", "deleted_at", "updated_at"])

            for farm in Farm.objects.filter(deleted_at__isnull=True):
                FarmCrop.objects.get_or_create(farm=farm, crop=crop)

            target_varieties = conf["varieties"]
            if target_varieties:
                crop.varieties_list.exclude(name__in=target_varieties).update(is_active=False, deleted_at=now)
            else:
                crop.varieties_list.filter(deleted_at__isnull=True).update(is_active=False, deleted_at=now)

            for idx, var_name in enumerate(target_varieties, start=1):
                variety, _ = crop.varieties_list.get_or_create(
                    name=var_name,
                    defaults={
                        "is_active": True,
                        "deleted_at": None,
                        "code": f"{idx:02d}-{crop.id}",
                        "est_days_to_harvest": 120 if crop.is_perennial else 90,
                    },
                )
                v_changed = False
                if not variety.is_active:
                    variety.is_active = True
                    v_changed = True
                if variety.deleted_at is not None:
                    variety.deleted_at = None
                    v_changed = True
                if not variety.code:
                    variety.code = f"{idx:02d}-{crop.id}"
                    v_changed = True
                if v_changed:
                    variety.save(update_fields=["is_active", "deleted_at", "code", "updated_at"])

            crops[crop_name] = crop

        Crop.objects.exclude(name__in=target_names).filter(deleted_at__isnull=True).update(is_active=False, deleted_at=now)
        return crops

    def _soft_cleanup(self, target_names):
        now = timezone.now()
        target_ids = list(Crop.objects.filter(name__in=target_names, deleted_at__isnull=True).values_list("id", flat=True))
        cleanup = {
            "daily_logs": DailyLog.objects.filter(deleted_at__isnull=True).update(is_active=False, deleted_at=now),
            "activities": Activity.objects.filter(deleted_at__isnull=True).update(is_active=False, deleted_at=now),
            "activity_items": ActivityItem.objects.filter(deleted_at__isnull=True).update(is_active=False, deleted_at=now),
            "activity_snapshots": ActivityCostSnapshot.objects.filter(deleted_at__isnull=True).update(is_active=False, deleted_at=now),
            "planned_activities": PlannedActivity.objects.filter(deleted_at__isnull=True).update(is_active=False, deleted_at=now),
            "planned_materials": PlannedMaterial.objects.filter(deleted_at__isnull=True).update(is_active=False, deleted_at=now),
            "budget_lines": CropPlanBudgetLine.objects.filter(deleted_at__isnull=True).update(is_active=False, deleted_at=now),
            "crop_plans": CropPlan.objects.filter(deleted_at__isnull=True).update(is_active=False, deleted_at=now),
        }
        if target_ids:
            cleanup["template_tasks"] = CropTemplateTask.objects.filter(template__crop_id__in=target_ids, deleted_at__isnull=True).update(is_active=False, deleted_at=now)
            cleanup["templates"] = CropTemplate.objects.filter(crop_id__in=target_ids, deleted_at__isnull=True).update(is_active=False, deleted_at=now)
            cleanup["tasks"] = Task.objects.filter(crop_id__in=target_ids, deleted_at__isnull=True).update(is_active=False, deleted_at=now)
            cleanup["crop_products"] = CropProduct.objects.filter(crop_id__in=target_ids, deleted_at__isnull=True).update(is_active=False, deleted_at=now)
            cleanup["crop_materials"] = CropMaterial.objects.filter(crop_id__in=target_ids, deleted_at__isnull=True).update(is_active=False, deleted_at=now)
        return cleanup

    def _ensure_season(self, year):
        season, _ = Season.objects.get_or_create(
            name=str(year),
            defaults={"start_date": date(year, 1, 1), "end_date": date(year, 12, 31), "is_active": True},
        )
        if not season.is_active:
            season.is_active = True
            season.save(update_fields=["is_active"])
        return season

    def _rebuild_catalog(self, crops, report, supported_tasks_table_exists):
        for crop_name, crop in crops.items():
            new_tasks = []
            for blueprint in self.TASKS[crop_name]:
                task, _ = Task.objects.get_or_create(
                    crop=crop,
                    stage=blueprint.stage,
                    name=blueprint.name,
                    defaults={
                        "requires_area": blueprint.requires_area,
                        "requires_machinery": blueprint.requires_machinery,
                        "requires_well": blueprint.requires_well,
                        "is_harvest_task": blueprint.is_harvest_task,
                        "requires_tree_count": blueprint.requires_tree_count,
                        "is_perennial_procedure": blueprint.is_perennial_procedure,
                        "is_asset_task": blueprint.is_asset_task,
                        "asset_type": blueprint.asset_type,
                        "target_asset_type": blueprint.target_asset_type,
                        "estimated_hours": Decimal("2.00"),
                        "is_active": True,
                        "deleted_at": None,
                    },
                )
                task.requires_area = blueprint.requires_area
                task.requires_machinery = blueprint.requires_machinery
                task.requires_well = blueprint.requires_well
                task.is_harvest_task = blueprint.is_harvest_task
                task.requires_tree_count = blueprint.requires_tree_count
                task.is_perennial_procedure = blueprint.is_perennial_procedure
                task.is_asset_task = blueprint.is_asset_task
                task.asset_type = blueprint.asset_type
                task.target_asset_type = blueprint.target_asset_type
                task.estimated_hours = Decimal("2.00")
                task.is_active = True
                task.deleted_at = None
                task.save()
                new_tasks.append(task)
                report["created"]["tasks"] += 1

            if supported_tasks_table_exists:
                crop.supported_tasks.set(new_tasks)

            item, _ = Item.objects.get_or_create(
                name=self.PRODUCTS[crop_name],
                group="Produce",
                defaults={'uom': 'kg', "unit_price": Decimal("0")},
            )
            product, _ = CropProduct.objects.get_or_create(
                crop=crop,
                name=self.PRODUCTS[crop_name],
                defaults={
                    "is_primary": True,
                    "pack_size": Decimal("1.00"),
                    "pack_uom": "kg",
                    "item": item,
                    "notes": "Operational product card",
                    "is_active": True,
                    "deleted_at": None,
                },
            )
            product.is_primary = True
            product.pack_size = Decimal("1.00")
            product.pack_uom='kg'
            product.item = item
            product.notes = "Operational product card"
            product.is_active = True
            product.deleted_at = None
            product.save()
            report["created"]["products"] += 1

            template, _ = CropTemplate.objects.get_or_create(
                crop=crop,
                name=f"قالب تشغيل {crop_name}",
                category=CropTemplate.CATEGORY_BUNDLE,
                defaults={
                    "description": "قالب تشغيل معياري متوافق مع الخطة الزراعية",
                    "metadata": {"crop": crop_name, "perennial": crop.is_perennial},
                    "is_active": True,
                    "deleted_at": None,
                },
            )
            template.description = "قالب تشغيل معياري متوافق مع الخطة الزراعية"
            template.metadata = {"crop": crop_name, "perennial": crop.is_perennial}
            template.is_active = True
            template.deleted_at = None
            template.save()
            report["created"]["templates"] += 1

            for task in new_tasks:
                template_task, _ = CropTemplateTask.objects.get_or_create(
                    template=template,
                    name=task.name,
                    defaults={
                        "task": task,
                        "stage": task.stage,
                        "estimated_hours": task.estimated_hours,
                        "notes": "Auto-linked from operational blueprint",
                        "is_active": True,
                        "deleted_at": None,
                    },
                )
                template_task.task = task
                template_task.stage = task.stage
                template_task.estimated_hours = task.estimated_hours
                template_task.notes = "Auto-linked from operational blueprint"
                template_task.is_active = True
                template_task.deleted_at = None
                template_task.save()
                report["created"]["template_tasks"] += 1

            for m_name, m_group, m_uom, m_qty in self.MATERIALS[crop_name]:
                mat_item, _ = Item.objects.get_or_create(
                    name=m_name,
                    group=m_group,
                    defaults={"uom": m_uom, "unit_price": Decimal("0")},
                )
                crop_material, _ = CropMaterial.objects.get_or_create(
                    crop=crop,
                    item=mat_item,
                    defaults={
                        "recommended_qty": m_qty,
                        "recommended_uom": m_uom,
                        "notes": "Auto standard material",
                        "is_active": True,
                        "deleted_at": None,
                    },
                )
                crop_material.recommended_qty = m_qty
                crop_material.recommended_uom = m_uom
                crop_material.notes = "Auto standard material"
                crop_material.is_active = True
                crop_material.deleted_at = None
                crop_material.save()
                report["created"]["materials"] += 1

    def _rebuild_plans(self, crops, season, report):
        for farm in Farm.objects.filter(deleted_at__isnull=True):
            farm_crops = list(
                Crop.objects.filter(
                    id__in=[c.id for c in crops.values()],
                    farm_links__farm=farm,
                    farm_links__deleted_at__isnull=True,
                    deleted_at__isnull=True,
                ).distinct()
            )
            if not farm_crops:
                continue

            orchard = Location.objects.filter(farm=farm, type="Orchard", deleted_at__isnull=True).first()
            field = Location.objects.filter(farm=farm, type__in=["Field", "Grain"], deleted_at__isnull=True).first()
            if orchard is None:
                orchard, _ = Location.objects.get_or_create(
                    farm=farm,
                    name="بستان رئيسي",
                    defaults={"type": "Orchard", "code": "ORCH-01"},
                )
            if field is None:
                field, _ = Location.objects.get_or_create(
                    farm=farm,
                    name="حقل رئيسي",
                    defaults={"type": "Field", "code": "FIELD-01"},
                )

            for crop in farm_crops:
                location = orchard if crop.is_perennial else field
                template = CropTemplate.objects.filter(crop=crop, deleted_at__isnull=True).order_by("id").first()
                tasks = list(Task.objects.filter(crop=crop, deleted_at__isnull=True).order_by("id"))
                materials = list(CropMaterial.objects.filter(crop=crop, deleted_at__isnull=True).select_related("item"))

                if crop.is_perennial:
                    budget_materials = Decimal("250000.0000")
                    budget_labor = Decimal("180000.0000")
                    budget_machinery = Decimal("80000.0000")
                    expected_yield = Decimal("12000.00")
                else:
                    budget_materials = Decimal("180000.0000")
                    budget_labor = Decimal("120000.0000")
                    budget_machinery = Decimal("90000.0000")
                    expected_yield = Decimal("8000.00")

                budget_total = budget_materials + budget_labor + budget_machinery

                plan = CropPlan.objects.filter(
                    farm=farm,
                    crop=crop,
                    location=location,
                    season=season,
                    deleted_at__isnull=True,
                ).first()
                if plan is None:
                    plan = CropPlan.objects.create(
                        farm=farm,
                        crop=crop,
                        location=location,
                        season=season,
                        name=f"خطة {crop.name} {season.name} - {farm.name}",
                        template=template,
                        start_date=season.start_date,
                        end_date=season.end_date,
                        area=Decimal("10.00"),
                        currency="YER",
                        budget_materials=budget_materials,
                        budget_labor=budget_labor,
                        budget_machinery=budget_machinery,
                        budget_total=budget_total,
                        budget_amount=budget_total,
                        expected_yield=expected_yield,
                        status="active",
                        notes="خطة تشغيل معيارية مولدة تلقائياً",
                        is_active=True,
                    )
                else:
                    plan.name = f"خطة {crop.name} {season.name} - {farm.name}"
                    plan.template = template
                    plan.start_date = season.start_date
                    plan.end_date = season.end_date
                    plan.area = Decimal("10.00")
                    plan.currency = "YER"
                    plan.budget_materials = budget_materials
                    plan.budget_labor = budget_labor
                    plan.budget_machinery = budget_machinery
                    plan.budget_total = budget_total
                    plan.budget_amount = budget_total
                    plan.expected_yield = expected_yield
                    plan.status = "active"
                    plan.notes = "خطة تشغيل معيارية مولدة تلقائياً"
                    plan.is_active = True
                    plan.deleted_at = None
                    plan.save()
                report["created"]["plans"] += 1

                step = max(1, int(300 / max(1, len(tasks))))
                for idx, task in enumerate(tasks):
                    PlannedActivity.objects.create(
                        crop_plan=plan,
                        task=task,
                        planned_date=season.start_date + timedelta(days=min(330, idx * step)),
                        estimated_hours=Decimal("2.00"),
                        notes="Planned from operational template",
                        is_active=True,
                    )
                    report["created"]["planned_activities"] += 1

                for mat in materials[:3]:
                    PlannedMaterial.objects.create(
                        crop_plan=plan,
                        item=mat.item,
                        planned_qty=mat.recommended_qty or Decimal("1.000"),
                        uom=mat.recommended_uom or mat.item.uom or "Unit",
                        is_active=True,
                    )
                    report["created"]["planned_materials"] += 1

                task_ref = tasks[0] if tasks else None
                for category, total_val, qty, uom in [
                    (CropPlanBudgetLine.CATEGORY_MATERIALS, budget_materials, Decimal("1.000"), "lot"),
                    (CropPlanBudgetLine.CATEGORY_LABOR, budget_labor, Decimal("30.000"), "surra"),
                    (CropPlanBudgetLine.CATEGORY_MACHINERY, budget_machinery, Decimal("20.000"), "hour"),
                ]:
                    rate = (total_val / qty).quantize(Decimal("0.0001"))
                    CropPlanBudgetLine.objects.create(
                        crop_plan=plan,
                        task=task_ref,
                        category=category,
                        qty_budget=qty,
                        uom=uom,
                        rate_budget=rate,
                        total_budget=total_val,
                        currency="YER",
                        is_active=True,
                    )
                    report["created"]["budget_lines"] += 1

    def _print_report(self, season_year, clean_ops, dry_run, supported_tasks_table_exists, report):
        self.stdout.write(self.style.SUCCESS("=== seed_operational_catalog completed ==="))
        self.stdout.write(f"season={season_year} clean_ops={clean_ops} dry_run={dry_run}")
        self.stdout.write(f"supported_tasks_table_exists={supported_tasks_table_exists}")
        if report["cleanup"]:
            self.stdout.write("Cleanup:")
            for key, val in report["cleanup"].items():
                self.stdout.write(f"  {key}: {val}")
        self.stdout.write("Created:")
        for key, val in report["created"].items():
            self.stdout.write(f"  {key}: {val}")
