from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from smart_agri.core.models import (
    Activity,
    Crop,
    CropProduct,
    CropVariety,
    DailyLog,
    Farm,
    Item,
    Location,
    LocationTreeStock,
    Supervisor,
    Task,
    TreeLossReason,
    TreeProductivityStatus,
    TreeStockEvent,
)
from smart_agri.core.services import TreeInventoryService


class Command(BaseCommand):
    help = "Bootstrap demo data for perennial tree inventory (crops, varieties, tasks, logs, and activities)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--farm",
            type=int,
            help="Target farm ID. When omitted the first farm with orchard locations will be used.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate changes without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        farm_id = options.get("farm")

        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode - no changes will be committed."))

        with transaction.atomic():
            farm = self._resolve_farm(farm_id)
            self.stdout.write(self.style.NOTICE(f"Selected farm: {farm.name} (ID {farm.id})"))

            statuses = self._ensure_productivity_statuses()
            loss_reasons = self._ensure_loss_reasons()
            crop = self._ensure_perennial_crop()
            varieties = self._ensure_varieties(crop)
            service_tasks = self._ensure_tasks(crop)
            products = self._ensure_crop_products(crop)

            self.stdout.write(self.style.SUCCESS(f"Created or updated {len(varieties)} crop varieties."))
            self.stdout.write(self.style.SUCCESS(f"Created or updated {len(products)} crop products."))
            if self._column_exists("core_activity", "tree_loss_reason_id"):
                created_logs, created_activities = self._seed_daily_logs(
                    farm=farm,
                    crop=crop,
                    varieties=varieties,
                    tasks=service_tasks,
                    statuses=statuses,
                    loss_reasons=loss_reasons,
                )
                self.stdout.write(self.style.SUCCESS(f"Prepared {len(created_logs)} daily logs."))
                self.stdout.write(self.style.SUCCESS(f"Generated {created_activities} activities with tree inventory events."))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "core_activity.tree_loss_reason_id column not found; seeding tree stock directly without daily logs."
                    )
                )
                stocked, events = self._seed_tree_stock_direct(
                    farm=farm,
                    varieties=varieties,
                    statuses=statuses,
                )
                self.stdout.write(self.style.SUCCESS(f"Prepared {stocked} tree stock records."))
                if events:
                    self.stdout.write(self.style.SUCCESS(f"Registered {events} tree stock events."))

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry-run complete - transaction rolled back."))

    # ------------------------------------------------------------------ #
    # Data preparation helpers
    # ------------------------------------------------------------------ #

    def _column_exists(self, table: str, column: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                  AND column_name = %s
                LIMIT 1
                """,
                [table, column],
            )
            return cursor.fetchone() is not None
    def _resolve_farm(self, farm_id: int | None) -> Farm:
        farm_qs = Farm.objects.filter(deleted_at__isnull=True)
        if farm_id is not None:
            farm = farm_qs.filter(id=farm_id).first()
            if not farm:
                raise CommandError(f"Farm with ID {farm_id} was not found.")
            return farm

        farm = (
            farm_qs.filter(locations__type__iexact="Orchard")
            .order_by("id")
            .distinct()
            .first()
        )
        if not farm:
            farm = farm_qs.order_by("id").first()
        if not farm:
            raise CommandError("No farms available to seed tree data.")
        return farm

    def _ensure_productivity_statuses(self) -> dict[str, TreeProductivityStatus]:
        payload = [
            {
                "code": "juvenile",
                "name_en": "Juvenile / Non-productive",
                "name_ar": "\u0623\u0634\u062c\u0627\u0631 \u063a\u064a\u0631 \u0645\u0646\u062a\u062c\u0629",
                "description": "Trees not yet bearing fruit.",
            },
            {
                "code": "productive",
                "name_en": "Productive",
                "name_ar": "\u0645\u0646\u062a\u062c\u0629",
                "description": "Trees in full production.",
            },
            {
                "code": "declining",
                "name_en": "Declining / Aged",
                "name_ar": "\u0645\u062a\u0631\u0627\u062c\u0639\u0629",
                "description": "Trees with reduced productivity.",
            },
            {
                "code": "dormant",
                "name_en": "Dormant / Under Maintenance",
                "name_ar": "\u062e\u0627\u0645\u0644\u0629 / \u062a\u062d\u062a \u0627\u0644\u0635\u064a\u0627\u0646\u0629",
                "description": "Trees temporarily inactive.",
            },
        ]
        statuses = {}
        for item in payload:
            obj, _ = TreeProductivityStatus.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name_en": item["name_en"],
                    "name_ar": item["name_ar"],
                    "description": item["description"],
                },
            )
            statuses[item["code"]] = obj
        return statuses

    def _ensure_loss_reasons(self) -> dict[str, TreeLossReason]:
        payload = [
            {
                "code": "pest",
                "name_en": "Pest / Disease",
                "name_ar": "\u0622\u0641\u0629 \u0623\u0648 \u0645\u0631\u0636",
                "description": "Tree lost due to pest or disease pressure.",
            },
            {
                "code": "water_stress",
                "name_en": "Water Stress",
                "name_ar": "\u0625\u062c\u0647\u0627\u062f \u0645\u0627\u0626\u064a",
                "description": "Tree lost due to irrigation issues.",
            },
            {
                "code": "storm_damage",
                "name_en": "Storm Damage",
                "name_ar": "\u0636\u0631\u0631 \u0639\u0627\u0635\u0641\u0629",
                "description": "Tree lost due to wind or storm event.",
            },
        ]
        reasons = {}
        for item in payload:
            obj, _ = TreeLossReason.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name_en": item["name_en"],
                    "name_ar": item["name_ar"],
                    "description": item["description"],
                },
            )
            reasons[item["code"]] = obj
        return reasons

    def _ensure_perennial_crop(self) -> Crop:
        """Seed all Yemeni perennial crops and return the primary one (نخيل التمر)."""
        crops_payload = [
            {"name": "نخيل التمر", "mode": "Open", "is_perennial": True},
            {"name": "مانجو", "mode": "Open", "is_perennial": True},
            {"name": "بن", "mode": "Open", "is_perennial": True},
            {"name": "رمان", "mode": "Open", "is_perennial": True},
            {"name": "سدر", "mode": "Open", "is_perennial": True},
            {"name": "لوز", "mode": "Open", "is_perennial": True},
            {"name": "قات", "mode": "Open", "is_perennial": True},
        ]
        primary = None
        for payload in crops_payload:
            crop, created = Crop.objects.update_or_create(
                name=payload["name"],
                mode=payload["mode"],
                defaults={"is_perennial": payload["is_perennial"]},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created crop '{payload['name']}' (perennial)."))
            if payload["name"] == "نخيل التمر":
                primary = crop
        return primary

    def _ensure_varieties(self, crop: Crop) -> list[CropVariety]:
        """Seed varieties for ALL perennial crops, return combined list."""
        varieties_map = {
            "نخيل التمر": [
                {"name": "خلاص الأحساء", "code": "PAL-001", "description": "تمور خلاص عالية الجودة."},
                {"name": "سكري القصيم", "code": "PAL-002", "description": "صنف سكري ذو إنتاجية مرتفعة."},
                {"name": "برحي البصرة", "code": "PAL-003", "description": "صنف مبكر ذو إنتاج طري."},
            ],
            "مانجو": [
                {"name": "تيمور", "code": "MNG-001", "description": "صنف مانجو تيمور اليمني الممتاز."},
                {"name": "قلب الثور", "code": "MNG-002", "description": "مانجو كبيرة الحجم للسوق المحلي."},
                {"name": "عويس", "code": "MNG-003", "description": "صنف مانجو عويس عالي السكر."},
            ],
            "بن": [
                {"name": "بن محلي", "code": "COF-001", "description": "بن يمني محلي عضوي."},
                {"name": "بن مطري", "code": "COF-002", "description": "بن المناطق المطرية (حراز/يافع)."},
            ],
            "رمان": [
                {"name": "رمان بلدي", "code": "POM-001", "description": "رمان بلدي يمني كبير الحجم."},
                {"name": "رمان طائفي", "code": "POM-002", "description": "صنف مستورد متأقلم."},
            ],
            "سدر": [
                {"name": "سدر بلدي", "code": "SID-001", "description": "عسل السدر اليمني الشهير."},
                {"name": "سدر بري", "code": "SID-002", "description": "سدر بري للمراعي والعسل."},
            ],
            "لوز": [
                {"name": "لوز بلدي", "code": "ALM-001", "description": "لوز يمني بلدي."},
                {"name": "لوز حضرمي", "code": "ALM-002", "description": "صنف لوز حضرموت."},
            ],
            "قات": [
                {"name": "قات رازحي", "code": "QAT-001", "description": "قات رازح/صعدة."},
                {"name": "قات حمدي", "code": "QAT-002", "description": "قات سهول تهامة."},
            ],
        }
        all_varieties = []
        for crop_name, variety_list in varieties_map.items():
            try:
                parent_crop = Crop.objects.get(name=crop_name, mode="Open")
            except Crop.DoesNotExist:
                continue
            for payload in variety_list:
                variety, _ = CropVariety.objects.update_or_create(
                    crop=parent_crop,
                    name=payload["name"],
                    defaults={
                        "code": payload["code"],
                        "description": payload["description"],
                    },
                )
                all_varieties.append(variety)
        return all_varieties

    def _ensure_tasks(self, crop: Crop) -> dict[str, Task]:
        tasks_payload = [
            {
                "key": "service",
                "name": "\u0635\u064a\u0627\u0646\u0629 \u0627\u0644\u0646\u062e\u064a\u0644 \u0627\u0644\u062f\u0648\u0631\u064a\u0629",
                "stage": "\u062e\u062f\u0645\u0629",
                "requires_tree_count": True,
                "is_perennial_procedure": True,
                "requires_well": True,
                "requires_machinery": False,
                "requires_area": False,
                "is_harvest_task": False,
            },
            {
                "key": "harvest",
                "name": "\u062d\u0635\u0627\u062f \u0627\u0644\u062a\u0645\u0648\u0631 \u0627\u0644\u064a\u062f\u0648\u064a",
                "stage": "\u062d\u0635\u0627\u062f",
                "requires_tree_count": True,
                "is_perennial_procedure": True,
                "requires_well": False,
                "requires_machinery": False,
                "requires_area": False,
                "is_harvest_task": True,
            },
        ]
        tasks = {}
        for payload in tasks_payload:
            task, _ = Task.objects.update_or_create(
                crop=crop,
                name=payload["name"],
                defaults={
                    "stage": payload["stage"],
                    "requires_tree_count": payload["requires_tree_count"],
                    "is_perennial_procedure": payload.get("is_perennial_procedure", payload["requires_tree_count"]),
                    "requires_machinery": payload["requires_machinery"],
                    "requires_well": payload["requires_well"],
                    "requires_area": payload["requires_area"],
                    "is_harvest_task": payload["is_harvest_task"],
                },
            )
            tasks[payload["key"]] = task
        return tasks

    def _seed_daily_logs(
        self,
        *,
        farm: Farm,
        crop: Crop,
        varieties: list[CropVariety],
        tasks: dict[str, Task],
        statuses: dict[str, TreeProductivityStatus],
        loss_reasons: dict[str, TreeLossReason],
    ) -> tuple[list[DailyLog], int]:
        locations = list(
            Location.objects.filter(
                farm=farm,
                deleted_at__isnull=True,
                type__iexact="Orchard",
            ).order_by("id")
        )
        if not locations:
            self.stdout.write(self.style.WARNING("No orchard locations found - creating a service location."))
            location, _ = Location.objects.get_or_create(
            farm=farm,
            name="Orchard A",
            defaults={"type": "Orchard", "code": "ORCH-A"},
            )

            locations = [location]

        supervisor = Supervisor.objects.filter(farm=farm, deleted_at__isnull=True).order_by("id").first()
        user_model = get_user_model()
        user = (
            user_model.objects.filter(is_superuser=True).order_by("id").first()
            or user_model.objects.order_by("id").first()
        )

        if user is None:
            raise CommandError("At least one user is required to assign created_by/updated_by fields.")

        service = TreeInventoryService()
        created_logs: list[DailyLog] = []
        created_activities = 0

        base_date = date.today() - timedelta(days=14)
        water_uoms = ["m3", "l"]
        fert_uoms = ["kg", "g"]
        harvest_item, _ = Item.objects.get_or_create(
            name=f"{crop.name} Harvest",
            defaults={"group": "Harvested Product", "uom": "kg"},
        )
        crop_product, _ = CropProduct.objects.get_or_create(crop=crop, item=harvest_item)

        for idx, location in enumerate(locations[: len(varieties)]):
            variety = varieties[idx % len(varieties)]
            planting_count = 80 + idx * 20
            service_hours = Decimal("5.5") + Decimal(str(idx))

            log, _ = DailyLog.objects.get_or_create(
                farm=farm,
                log_date=base_date + timedelta(days=idx * 3),
                defaults={
                    "supervisor": supervisor,
                    "notes": "\u0633\u062c\u0644 \u062a\u062c\u0631\u064a\u0628\u064a \u0644\u0646\u0634\u0627\u0637 \u0627\u0644\u0646\u062e\u064a\u0644.",
                    "created_by": user,
                    "updated_by": user,
                },
            )
            created_logs.append(log)

            service_activity = Activity.objects.filter(
                log=log,
                task=tasks["service"],
                location=location,
                variety=variety,
                tree_count_delta=planting_count,
                activity_tree_count=planting_count,
            ).first()
            if service_activity is None:
                service_activity = Activity.objects.create(
                    log=log,
                    crop=crop,
                    task=tasks["service"],
                    location=location,
                    variety=variety,
                    tree_count_delta=planting_count,
                    activity_tree_count=planting_count,
                    days_spent=service_hours,
                    water_volume=Decimal("12.0") + Decimal(idx),
                    water_uom=random.choice(water_uoms),
                    fertilizer_quantity=Decimal("2.5") + Decimal("0.5") * idx,
                    fertilizer_uom=random.choice(fert_uoms),
                    team="\u0641\u0631\u064a\u0642 \u0627\u0644\u0623\u0634\u062c\u0627\u0631",
                    created_by=user,
                    updated_by=user,
                )
                service.reconcile_activity(activity=service_activity, user=user)
                created_activities += 1

            self._tag_stock(
                location=location,
                variety=variety,
                status=statuses.get("productive"),
                log_date=log.log_date,
            )

            loss_activity = Activity.objects.filter(
                log=log,
                task=tasks["service"],
                location=location,
                variety=variety,
                tree_count_delta=-5,
            ).first()
            if loss_activity is None:
                loss_activity = Activity.objects.create(
                    log=log,
                    crop=crop,
                    task=tasks["service"],
                    location=location,
                    variety=variety,
                    tree_count_delta=-5,
                    activity_tree_count=planting_count - 5,
                    tree_loss_reason=loss_reasons["pest"],
                    days_spent=Decimal("2.5"),
                    water_volume=Decimal("1.0"),
                    water_uom="m3",
                    fertilizer_quantity=Decimal("0.0"),
                    fertilizer_uom="kg",
                    team="\u0641\u0631\u064a\u0642 \u0627\u0644\u0623\u0634\u062c\u0627\u0631",
                    created_by=user,
                    updated_by=user,
                )
                service.reconcile_activity(activity=loss_activity, user=user)
                created_activities += 1

            harvest_activity = Activity.objects.filter(
                log=log,
                task=tasks["harvest"],
                location=location,
                variety=variety,
            ).first()
            if harvest_activity is None:
                harvest_activity = Activity.objects.create(
                    log=log,
                    crop=crop,
                    task=tasks["harvest"],
                    location=location,
                    variety=variety,
                    tree_count_delta=0,
                    activity_tree_count=planting_count - 5,
                    harvest_quantity=Decimal("185.0") + Decimal(idx * 10),
                    product=crop_product,
                    team="\u0641\u0631\u064a\u0642 \u0627\u0644\u062d\u0635\u0627\u062f",
                    created_by=user,
                    updated_by=user,
                )
                service.reconcile_activity(activity=harvest_activity, user=user)
                created_activities += 1

        return created_logs, created_activities

    def _ensure_crop_products(self, crop):
        from smart_agri.core.models import CropProduct

        products_created = []
        for crop_code, config in self.CROP_VARIETIES.items():
            db_crop = self.CROP_REFS.get(crop_code)
            if not db_crop:
                continue

            products = config.get("products", [])
            for p in products:
                prod, created = CropProduct.objects.get_or_create(
                    crop=db_crop,
                    name=p["name_ar"],
                    defaults={
                        "pack_uom": p.get("pack_uom", "box"),
                        "pack_size": p.get("unit_weight_kg", 1.0),
                    }
                )
                if not created and (prod.pack_uom != p.get("pack_uom", "box")):
                    prod.pack_uom = p.get("pack_uom", "box")
                    prod.save()
                products_created.append(prod)
        return products_created

    def _seed_tree_stock_direct(
        self,
        *,
        farm: Farm,
        varieties: list[CropVariety],
        statuses: dict[str, TreeProductivityStatus],
    ) -> tuple[int, int]:
        locations = list(
            Location.objects.filter(
                farm=farm,
                deleted_at__isnull=True,
                type__iexact="Orchard",
            ).order_by("id")
        )
        if not locations:
            location, _ = Location.objects.get_or_create(
                farm=farm,
                name="Orchard A",
                defaults={"type": "Orchard", "code": "ORCH-A"},
            )
            locations = [location]

        baseline_date = date.today() - timedelta(days=365)
        productive_status = statuses.get("productive")

        stock_count = 0
        event_count = 0

        for idx, location in enumerate(locations[: len(varieties)]):
            variety = varieties[idx % len(varieties)]
            planted = 80 + idx * 20
            remaining = max(planted - 5, 0)

            stock, created = LocationTreeStock.objects.update_or_create(
                location=location,
                crop_variety=variety,
                defaults={
                    "current_tree_count": remaining,
                    "productivity_status": productive_status,
                    "planting_date": baseline_date,
                    "source": "Nursery (demo)",
                    "notes": "Seeded demo tree balance.",
                },
            )

            if created:
                stock_count += 1
            else:
                update_fields: list[str] = []
                if stock.current_tree_count != remaining:
                    stock.current_tree_count = remaining
                    update_fields.append("current_tree_count")
                if productive_status and stock.productivity_status_id != productive_status.id:
                    stock.productivity_status = productive_status
                    update_fields.append("productivity_status")
                if not stock.planting_date:
                    stock.planting_date = baseline_date
                    update_fields.append("planting_date")
                if not stock.source:
                    stock.source = "Nursery (demo)"
                    update_fields.append("source")
                if not stock.notes:
                    stock.notes = "Seeded demo tree balance."
                    update_fields.append("notes")
                if update_fields:
                    update_fields.append("updated_at")
                    stock.save(update_fields=update_fields)

            event_defaults = {
                "event_timestamp": timezone.make_aware(
                    datetime.combine(baseline_date, datetime.min.time())
                )
                if baseline_date
                else timezone.now(),
                "tree_count_delta": planted,
                "resulting_tree_count": remaining,
                "planting_date": baseline_date,
                "source": stock.source or "Nursery (demo)",
                "notes": "Initial seeding entry.",
            }
            event, created_event = TreeStockEvent.objects.get_or_create(
                location_tree_stock=stock,
                event_type=TreeStockEvent.PLANTING,
                defaults=event_defaults,
            )
            if created_event:
                event_count += 1
            else:
                update_fields: list[str] = []
                for field in ("tree_count_delta", "resulting_tree_count", "planting_date", "source", "notes"):
                    target = event_defaults.get(field)
                    if target is not None and getattr(event, field) != target:
                        setattr(event, field, target)
                        update_fields.append(field)
                timestamp_default = event_defaults["event_timestamp"]
                if timestamp_default and event.event_timestamp != timestamp_default:
                    event.event_timestamp = timestamp_default
                    update_fields.append("event_timestamp")
                if update_fields:
                    event.save(update_fields=update_fields)

        return stock_count, event_count
    def _tag_stock(self, *, location: Location, variety: CropVariety, status: TreeProductivityStatus | None, log_date: date):
        if status is None:
            return
        stock = (
            LocationTreeStock.objects.filter(location=location, crop_variety=variety)
            .order_by("-updated_at")
            .first()
        )
        if not stock:
            return
        dirty = False
        if stock.productivity_status_id != status.id:
            stock.productivity_status = status
            dirty = True
        if stock.planting_date is None:
            stock.planting_date = log_date - timedelta(days=30)
            dirty = True
        if not stock.source:
            stock.source = "مشتل العرض"
            dirty = True
        if dirty:
            stock.save(update_fields=["productivity_status", "planting_date", "source", "updated_at"])





















