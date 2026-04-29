from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.constants import DailyLogStatus, StandardUOM, SyncCategory, SyncStatus
from smart_agri.core.models import (
    Activity,
    DailyLog,
    Farm,
    FarmCrop,
    Location,
    LocationTreeStock,
    OfflineSyncQuarantine,
    SyncConflictDLQ,
    SyncRecord,
    Task,
    TreeProductivityStatus,
    TreeServiceCoverage,
)
from smart_agri.core.models.activity import ActivityItem, ActivityLocation
from smart_agri.core.models.crop import Crop, CropProduct, CropVariety
from smart_agri.core.models.farm import Asset, LocationWell
from smart_agri.core.models.planning import CropPlan, CropPlanLocation, PlannedActivity, Season
from smart_agri.core.models.settings import FarmSettings, LaborRate, MachineRate, Supervisor
from smart_agri.core.services.custody_transfer_service import CustodyTransferService
from smart_agri.finance.models import FiscalPeriod, FiscalYear
from smart_agri.inventory.models import FuelLog, Item, ItemInventory, MaterialType, TankCalibration, Unit


DEMO_SLUG = "simple-offline-demo-farm"
DEMO_USER = "simple_offline_demo"
DEMO_DEVICE = "simple-offline-demo-web"
DEMO_LOG_REQUEST_ID = "simple-offline-demo-log-1"
DEMO_ACTIVITY_IDEMPOTENCY = uuid.UUID("f22c37a4-5f27-4d8e-a4e1-7d59ffb09e01")


class Command(BaseCommand):
    help = "Seed idempotent SIMPLE/offline demo data for manual QA and evidence runs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-demo",
            action="store_true",
            help="Reset demo evidence records for the simple-offline-demo-farm scope before reseeding.",
        )
        parser.add_argument(
            "--with-offline-fixtures",
            action="store_true",
            help="Seed server-side SyncRecord/DLQ/quarantine fixtures that mirror offline queue states.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        user = self._ensure_user()
        farm = self._ensure_farm(user)
        if options["reset_demo"]:
            self._reset_demo_evidence(farm=farm, user=user)

        settings_obj = self._ensure_settings(farm)
        season = self._ensure_season()
        location, warehouse = self._ensure_locations(farm)
        supervisor = self._ensure_supervisor(farm)
        crop, variety, product = self._ensure_crop(farm)
        plan = self._ensure_plan(farm=farm, crop=crop, season=season, location=location, user=user)
        task = self._ensure_all_cards_task(crop)
        self._ensure_task_plan_link(plan=plan, task=task)
        assets = self._ensure_assets(farm=farm, location=location)
        items = self._ensure_items(farm=farm, warehouse=warehouse)
        self._ensure_rates(farm=farm, machine=assets["machine"])
        self._ensure_supervisor_custody(
            farm=farm,
            supervisor=supervisor,
            item=items["fertilizer"],
            warehouse=warehouse,
            user=user,
        )
        self._ensure_fiscal_period(farm=farm, target_date=timezone.localdate())
        self._ensure_tree_stock(location=location, variety=variety)
        self._ensure_fuel_fixture(farm=farm, supervisor=supervisor, tank=assets["tank"])
        log, activity = self._ensure_daily_log_cycle(
            farm=farm,
            user=user,
            supervisor=supervisor,
            location=location,
            crop=crop,
            variety=variety,
            product=product,
            plan=plan,
            task=task,
            machine=assets["machine"],
            well=assets["well"],
            item=items["fertilizer"],
        )

        offline_summary = {}
        if options["with_offline_fixtures"]:
            offline_summary = self._ensure_offline_fixtures(farm=farm, user=user, supervisor=supervisor, location=location, crop=crop, variety=variety, task=task)

        self.stdout.write(self.style.SUCCESS("Seeded SIMPLE/offline demo data."))
        self.stdout.write(f"farm_id={farm.id} slug={farm.slug} mode={settings_obj.mode}")
        self.stdout.write(f"user={user.username} password=DemoOffline2026!")
        self.stdout.write(f"location_id={location.id} crop_id={crop.id} variety_id={variety.id}")
        self.stdout.write(f"crop_plan_id={plan.id} task_id={task.id} daily_log_id={log.id} activity_id={activity.id}")
        if offline_summary:
            self.stdout.write(
                "offline_fixtures="
                + ",".join(f"{key}:{value}" for key, value in sorted(offline_summary.items()))
            )

    def _ensure_user(self):
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username=DEMO_USER,
            defaults={
                "email": "simple.offline.demo@example.test",
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Simple",
                "last_name": "Offline Demo",
            },
        )
        changed = []
        if not user.is_staff:
            user.is_staff = True
            changed.append("is_staff")
        if not user.is_superuser:
            user.is_superuser = True
            changed.append("is_superuser")
        user.set_password("DemoOffline2026!")
        changed.append("password")
        user.save(update_fields=list(dict.fromkeys(changed)))
        return user

    def _ensure_farm(self, user):
        farm = Farm.objects.filter(slug=DEMO_SLUG).order_by("id").first()
        defaults = {
            "name": "Simple Offline Demo Farm",
            "slug": DEMO_SLUG,
            "region": "Sardud Demo",
            "area": Decimal("24.00"),
            "tier": Farm.TIER_SMALL,
            "zakat_rule": Farm.ZAKAT_HALF_TITHE,
            "is_organization": False,
            "operational_mode": FarmSettings.MODE_SIMPLE,
            "sensing_mode": "MANUAL",
            "organization_id": None,
            "description": "Demo-only farm for SIMPLE offline readiness verification.",
        }
        if farm is None:
            farm = Farm.objects.create(**defaults)
        else:
            for field, value in defaults.items():
                setattr(farm, field, value)
            farm.deleted_at = None
            farm.is_active = True
            farm.save()
        FarmMembership.objects.update_or_create(user=user, farm=farm, defaults={"role": "Manager"})
        return farm

    def _ensure_settings(self, farm):
        settings_obj, _ = FarmSettings.objects.get_or_create(farm=farm)
        settings_obj.mode = FarmSettings.MODE_SIMPLE
        settings_obj.cost_visibility = FarmSettings.COST_VISIBILITY_RATIOS_ONLY
        settings_obj.variance_behavior = FarmSettings.VARIANCE_BEHAVIOR_WARN
        settings_obj.approval_profile = FarmSettings.APPROVAL_PROFILE_TIERED
        settings_obj.contract_mode = FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY
        settings_obj.treasury_visibility = FarmSettings.TREASURY_VISIBILITY_HIDDEN
        settings_obj.fixed_asset_mode = FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY
        settings_obj.show_finance_in_simple = False
        settings_obj.show_stock_in_simple = False
        settings_obj.show_employees_in_simple = False
        settings_obj.show_daily_log_smart_card = True
        settings_obj.show_operational_alerts = True
        settings_obj.enable_petty_cash = True
        settings_obj.enable_sharecropping = True
        settings_obj.allow_multi_location_activities = True
        settings_obj.allow_cross_plan_activities = False
        settings_obj.offline_cache_retention_days = 7
        settings_obj.synced_draft_retention_days = 3
        settings_obj.dead_letter_retention_days = 14
        settings_obj.enable_offline_media_purge = True
        settings_obj.enable_offline_conflict_resolution = True
        settings_obj.enable_local_purge_audit = True
        settings_obj.default_irrigation_power_source = FarmSettings.IRRIGATION_POWER_SOLAR
        settings_obj.save()
        return settings_obj

    def _ensure_season(self):
        today = timezone.localdate()
        season, _ = Season.objects.update_or_create(
            name=f"Demo Season {today.year}",
            defaults={
                "start_date": date(today.year, 1, 1),
                "end_date": date(today.year, 12, 31),
                "is_active": True,
                "description": "Demo season for SIMPLE/offline audit.",
            },
        )
        return season

    def _ensure_locations(self, farm):
        location, _ = Location.objects.update_or_create(
            farm=farm,
            name="Location 1 - Mango SIMPLE Demo",
            defaults={"type": "Orchard", "code": "DEMO-LOC-1", "latitude": Decimal("15.369400"), "longitude": Decimal("44.191000")},
        )
        warehouse, _ = Location.objects.update_or_create(
            farm=farm,
            name="Demo Offline Warehouse",
            defaults={"type": "Warehouse", "code": "DEMO-WH-1"},
        )
        return location, warehouse

    def _ensure_supervisor(self, farm):
        supervisor, _ = Supervisor.objects.update_or_create(
            code="DEMO-SUP-OFFLINE",
            defaults={"farm": farm, "name": "Demo Field Supervisor"},
        )
        return supervisor

    def _ensure_crop(self, farm):
        crop, _ = Crop.objects.update_or_create(
            name="Mango Offline Demo",
            mode="Open",
            defaults={
                "is_perennial": True,
                "max_yield_per_ha": Decimal("18.000"),
                "max_yield_per_tree": Decimal("45.000"),
                "phenological_stages": {"stages": ["vegetative", "flowering", "fruiting"]},
            },
        )
        FarmCrop.objects.get_or_create(farm=farm, crop=crop)
        variety, _ = CropVariety.objects.update_or_create(
            crop=crop,
            name="Demo Mango Variety",
            defaults={
                "code": "DM-MNG",
                "est_days_to_harvest": 365,
                "expected_yield_per_ha": Decimal("12.00"),
                "description": "Demo perennial variety for offline SIMPLE QA.",
            },
        )
        produce_item, _ = Item.objects.update_or_create(
            name="Demo Mango Produce",
            group="Produce",
            defaults={
                "material_type": MaterialType.OTHER,
                "uom": StandardUOM.KG,
                "unit_price": Decimal("900.000"),
                "is_saleable": True,
            },
        )
        product, _ = CropProduct.objects.update_or_create(
            crop=crop,
            name="Demo Mango Pack",
            farm=farm,
            defaults={
                "item": produce_item,
                "is_primary": True,
                "pack_size": Decimal("1.00"),
                "pack_uom": StandardUOM.KG,
                "packing_type": "crate",
                "quality_grade": "A",
                "reference_price": Decimal("900.00"),
            },
        )
        return crop, variety, product

    def _ensure_plan(self, *, farm, crop, season, location, user):
        today = timezone.localdate()
        plan, _ = CropPlan.objects.update_or_create(
            farm=farm,
            crop=crop,
            name=f"Demo Mango SIMPLE Offline Plan {today.year}",
            defaults={
                "season": season,
                "start_date": date(today.year, 1, 1),
                "end_date": date(today.year, 12, 31),
                "area": Decimal("6.00"),
                "budget_materials": Decimal("150000.0000"),
                "budget_labor": Decimal("180000.0000"),
                "budget_machinery": Decimal("90000.0000"),
                "budget_total": Decimal("420000.0000"),
                "expected_yield": Decimal("7200.00"),
                "yield_unit": StandardUOM.KG,
                "status": "active",
                "notes": "Demo-only SIMPLE/offline plan.",
                "created_by": user,
                "updated_by": user,
            },
        )
        CropPlanLocation.objects.update_or_create(
            crop_plan=plan,
            location=location,
            defaults={"assigned_area": Decimal("6.00")},
        )
        return plan

    def _ensure_all_cards_task(self, crop):
        task, _ = Task.objects.update_or_create(
            crop=crop,
            stage="Demo Execution",
            name="All Smart Cards Demo",
            defaults={
                "requires_area": True,
                "requires_machinery": True,
                "requires_well": True,
                "requires_tree_count": True,
                "is_harvest_task": True,
                "is_perennial_procedure": True,
                "is_asset_task": True,
                "archetype": Task.Archetype.PERENNIAL_SERVICE,
                "asset_type": "tractor",
                "target_asset_type": Task.AssetType.MACHINE,
                "estimated_hours": Decimal("4.00"),
            },
        )
        contract = task.build_default_contract()
        for card in (
            "execution",
            "materials",
            "labor",
            "well",
            "machinery",
            "fuel",
            "perennial",
            "harvest",
            "control",
            "variance",
            "financial_trace",
        ):
            contract.setdefault("smart_cards", {}).setdefault(card, {})["enabled"] = True
        contract.setdefault("input_profile", {}).update(
            {
                "requires_well": True,
                "requires_machinery": True,
                "requires_area": True,
                "requires_tree_count": True,
                "is_harvest_task": True,
                "is_perennial_procedure": True,
                "requires_materials": True,
                "requires_labor_batch": True,
                "requires_service_rows": True,
            }
        )
        task.task_contract = contract
        task.save(update_fields=["task_contract", "task_contract_version", "updated_at"])
        return task

    def _ensure_task_plan_link(self, *, plan, task):
        PlannedActivity.objects.update_or_create(
            crop_plan=plan,
            task=task,
            planned_date=timezone.localdate(),
            defaults={"estimated_hours": Decimal("4.00")},
        )

    def _ensure_assets(self, *, farm, location):
        well, _ = Asset.objects.update_or_create(
            farm=farm,
            code="DEMO-WELL-1",
            defaults={
                "category": "Well",
                "asset_type": "well",
                "name": "Demo Well 1",
                "purchase_value": Decimal("0.00"),
                "status": "active",
            },
        )
        LocationWell.objects.update_or_create(
            location=location,
            asset=well,
            defaults={
                "well_depth": Decimal("120.00"),
                "pump_type": "solar",
                "capacity_lps": Decimal("8.50"),
                "status": "active",
                "is_operational": True,
                "notes": "Demo well for SIMPLE/offline audit.",
            },
        )
        machine, _ = Asset.objects.update_or_create(
            farm=farm,
            code="DEMO-TR-1",
            defaults={
                "category": "Machinery",
                "asset_type": "tractor",
                "name": "Demo Tractor 1",
                "purchase_value": Decimal("2500000.00"),
                "operational_cost_per_hour": Decimal("8500.00"),
                "status": "active",
            },
        )
        tank, _ = Asset.objects.update_or_create(
            farm=farm,
            code="DEMO-TANK-1",
            defaults={
                "category": "Fuel",
                "asset_type": "tank",
                "name": "Demo Diesel Tank 1",
                "purchase_value": Decimal("0.00"),
                "status": "active",
            },
        )
        return {"well": well, "machine": machine, "tank": tank}

    def _ensure_items(self, *, farm, warehouse):
        kg, _ = Unit.objects.update_or_create(
            code="DEMO_KG",
            defaults={"name": "Demo kilogram", "symbol": "kg", "category": Unit.CATEGORY_MASS, "precision": 3},
        )
        fertilizer, _ = Item.objects.update_or_create(
            name="Demo Mango Fertilizer",
            group="Fertilizer",
            defaults={
                "material_type": MaterialType.FERTILIZER,
                "uom": StandardUOM.KG,
                "unit": kg,
                "unit_price": Decimal("1200.000"),
                "reorder_level": Decimal("25.000"),
                "requires_batch_tracking": False,
            },
        )
        inventory, _ = ItemInventory.objects.get_or_create(
            farm=farm,
            location=warehouse,
            item=fertilizer,
            crop_plan=None,
            defaults={"qty": Decimal("500.000"), "uom": StandardUOM.KG},
        )
        if inventory.qty < Decimal("500.000") or inventory.uom != StandardUOM.KG:
            inventory.qty = Decimal("500.000")
            inventory.uom = StandardUOM.KG
            inventory.save(update_fields=["qty", "uom", "updated_at"])
        return {"fertilizer": fertilizer, "warehouse_inventory": inventory}

    def _ensure_rates(self, *, farm, machine):
        LaborRate.objects.update_or_create(
            farm=farm,
            role_name="Demo Casual Batch",
            effective_date=date(timezone.localdate().year, 1, 1),
            defaults={
                "daily_rate": Decimal("5000.0000"),
                "cost_per_hour": Decimal("625.0000"),
                "currency": "YER",
            },
        )
        MachineRate.objects.update_or_create(
            asset=machine,
            defaults={
                "daily_rate": Decimal("35000.0000"),
                "cost_per_hour": Decimal("8500.0000"),
                "fuel_consumption_rate": Decimal("4.5000"),
                "currency": "YER",
            },
        )

    def _ensure_supervisor_custody(self, *, farm, supervisor, item, warehouse, user):
        current_balance = CustodyTransferService.get_item_custody_balance(
            farm=farm,
            supervisor=supervisor,
            item=item,
        )
        if current_balance >= Decimal("25.000"):
            return
        transfer = CustodyTransferService.issue_transfer(
            farm=farm,
            supervisor=supervisor,
            item=item,
            source_location=warehouse,
            qty=Decimal("25.000"),
            actor=user,
            batch_number="",
            note="Demo SIMPLE/offline supervisor custody top-up.",
            allow_top_up=True,
            idempotency_key="simple-offline-demo-custody-fertilizer",
        )
        CustodyTransferService.accept_transfer(
            transfer=transfer,
            actor=user,
            note="Accepted for SIMPLE/offline demo DailyLog material card.",
        )

    def _ensure_fiscal_period(self, *, farm, target_date):
        fiscal_year, _ = FiscalYear.objects.get_or_create(
            farm=farm,
            year=target_date.year,
            defaults={"start_date": date(target_date.year, 1, 1), "end_date": date(target_date.year, 12, 31)},
        )
        if fiscal_year.start_date != date(target_date.year, 1, 1) or fiscal_year.end_date != date(target_date.year, 12, 31):
            fiscal_year.start_date = date(target_date.year, 1, 1)
            fiscal_year.end_date = date(target_date.year, 12, 31)
            fiscal_year.save(update_fields=["start_date", "end_date", "updated_at"])
        month_end = monthrange(target_date.year, target_date.month)[1]
        period, _ = FiscalPeriod.objects.get_or_create(
            fiscal_year=fiscal_year,
            month=target_date.month,
            defaults={
                "start_date": date(target_date.year, target_date.month, 1),
                "end_date": date(target_date.year, target_date.month, month_end),
                "status": FiscalPeriod.STATUS_OPEN,
                "is_closed": False,
            },
        )
        if period.status != FiscalPeriod.STATUS_OPEN:
            period._allow_reopen = True
            period.status = FiscalPeriod.STATUS_OPEN
            period.is_closed = False
            period.save(update_fields=["status", "is_closed", "updated_at"])

    def _ensure_tree_stock(self, *, location, variety):
        status, _ = TreeProductivityStatus.objects.update_or_create(
            code="DEMO_PRODUCTIVE",
            defaults={"name_en": "Demo Productive", "name_ar": "Demo Productive", "description": "Demo productivity status."},
        )
        stock, _ = LocationTreeStock.objects.update_or_create(
            location=location,
            crop_variety=variety,
            defaults={
                "current_tree_count": 222,
                "productivity_status": status,
                "planting_date": date(timezone.localdate().year - 3, 1, 15),
                "source": "simple_offline_demo_seed",
                "notes": "Demo stock aligned with DailyLog service rows.",
            },
        )
        return stock

    def _ensure_fuel_fixture(self, *, farm, supervisor, tank):
        for cm, liters in (("80.00", "800.0000"), ("90.00", "900.0000"), ("100.00", "1000.0000")):
            TankCalibration.objects.update_or_create(
                asset=tank,
                cm_reading=Decimal(cm),
                defaults={"liters_volume": Decimal(liters)},
            )
        reading_dt = timezone.make_aware(datetime.combine(timezone.localdate(), time(hour=8, minute=0)))
        fuel_log = FuelLog.objects.filter(
            farm=farm,
            asset_tank=tank,
            supervisor=supervisor,
            reading_date=reading_dt,
        ).first()
        if fuel_log is None:
            FuelLog.objects.create(
                farm=farm,
                asset_tank=tank,
                supervisor=supervisor,
                reading_date=reading_dt,
                measurement_method=FuelLog.MEASUREMENT_METHOD_DIPSTICK,
                reading_start_cm=Decimal("100.00"),
                reading_end_cm=Decimal("90.00"),
            )

    def _ensure_daily_log_cycle(self, *, farm, user, supervisor, location, crop, variety, product, plan, task, machine, well, item):
        log, _ = DailyLog.objects.update_or_create(
            mobile_request_id=DEMO_LOG_REQUEST_ID,
            defaults={
                "farm": farm,
                "supervisor": supervisor,
                "log_date": timezone.localdate(),
                "status": DailyLogStatus.SUBMITTED,
                "notes": "Demo online/offline DailyLog for SIMPLE readiness.",
                "variance_status": "WARNING",
                "variance_note": "Demo variance posture only; no SIMPLE finance authoring.",
                "created_by": user,
                "updated_by": user,
                "device_timestamp": timezone.now() - timedelta(minutes=20),
                "observation_data": {
                    "demo_seed": True,
                    "offline_supported": True,
                    "source": "seed_simple_offline_demo_data",
                },
            },
        )
        activity, _ = Activity.objects.update_or_create(
            idempotency_key=DEMO_ACTIVITY_IDEMPOTENCY,
            defaults={
                "log": log,
                "crop": crop,
                "crop_plan": plan,
                "task": task,
                "product": product,
                "crop_variety": variety,
                "asset": machine,
                "well_asset": well,
                "task_contract_version": task.task_contract_version,
                "task_contract_snapshot": task.get_effective_contract(),
                "tree_count_delta": 0,
                "activity_tree_count": 222,
                "days_spent": Decimal("1.00"),
                "agreed_daily_rate": Decimal("5000.00"),
                "cost_materials": Decimal("3600.0000"),
                "cost_labor": Decimal("110000.0000"),
                "cost_machinery": Decimal("17000.0000"),
                "cost_wastage": Decimal("0.0000"),
                "cost_total": Decimal("130600.0000"),
                "created_by": user,
                "updated_by": user,
                "device_timestamp": timezone.now() - timedelta(minutes=19),
                "data": {
                    "demo_seed": True,
                    "locations": [location.id],
                    "labor_entry_mode": "CASUAL_BATCH",
                    "casual_workers_count": "22",
                    "surrah_count": "1",
                    "machine_hours": "2",
                    "water_volume": "2",
                    "is_solar_powered": True,
                    "harvest_quantity": "22",
                    "service_counts_payload": [
                        {
                            "variety_id": variety.id,
                            "location_id": location.id,
                            "service_count": "222",
                            "service_type": TreeServiceCoverage.GENERAL,
                            "service_scope": TreeServiceCoverage.SCOPE_LOCATION,
                            "distribution_mode": TreeServiceCoverage.DISTRIBUTION_UNIFORM,
                        }
                    ],
                },
            },
        )
        ActivityLocation.objects.update_or_create(
            activity=activity,
            location=location,
            defaults={"allocated_percentage": Decimal("100.00")},
        )
        coverage, _ = TreeServiceCoverage.objects.update_or_create(
            activity=activity,
            location=location,
            crop_variety=variety,
            service_type=TreeServiceCoverage.GENERAL,
            defaults={
                "farm": farm,
                "target_scope": TreeServiceCoverage.SCOPE_LOCATION,
                "trees_covered": 222,
                "area_covered_ha": Decimal("6.0000"),
                "distribution_mode": TreeServiceCoverage.DISTRIBUTION_UNIFORM,
                "distribution_factor": Decimal("0.0000"),
                "date": log.log_date,
                "notes": "Demo coverage for all smart-card task.",
                "total_before": 222,
                "total_after": 222,
            },
        )
        item_row = ActivityItem.objects.filter(activity=activity, item=item).first()
        if item_row is None:
            ActivityItem.objects.create(
                activity=activity,
                item=item,
                qty=Decimal("3.000"),
                applied_qty=Decimal("3.000"),
                uom=StandardUOM.KG,
                batch_number="",
                cost_per_unit=Decimal("1200.0000"),
            )
        else:
            item_row.qty = Decimal("3.000")
            item_row.applied_qty = Decimal("3.000")
            item_row.uom = StandardUOM.KG
            item_row.batch_number = ""
            item_row.cost_per_unit = Decimal("1200.0000")
            item_row.save()
        return log, activity

    def _ensure_offline_fixtures(self, *, farm, user, supervisor, location, crop, variety, task):
        base_payload = {
            "uuid": "9912181a-31b2-4701-8f18-e1c06e1f1426",
            "payload_uuid": "9912181a-31b2-4701-8f18-e1c06e1f1426",
            "farm_id": farm.id,
            "supervisor_id": supervisor.id,
            "device_id": DEMO_DEVICE,
            "log": {"log_date": timezone.localdate().isoformat(), "notes": "demo offline replay payload"},
            "activity": {
                "crop": crop.id,
                "task": task.id,
                "locations": [location.id],
                "variety_id": variety.id,
                "service_counts_payload": [
                    {
                        "location_id": location.id,
                        "variety_id": variety.id,
                        "service_count": "222",
                        "service_type": TreeServiceCoverage.GENERAL,
                        "service_scope": TreeServiceCoverage.SCOPE_LOCATION,
                        "distribution_mode": TreeServiceCoverage.DISTRIBUTION_UNIFORM,
                    }
                ],
            },
        }
        records = [
            ("demo-offline-pending", SyncStatus.PENDING, 0, ""),
            ("demo-offline-stale-syncing", SyncStatus.PENDING, 1, "Recovered stale syncing item; should replay automatically."),
            ("demo-offline-dead-letter-retryable", SyncStatus.FAILED, 1, "Demo retryable dead letter."),
            ("demo-offline-idempotency-rotation", SyncStatus.PENDING, 0, "Previous key rotated after IDEMPOTENCY_MISMATCH."),
        ]
        for reference, status, attempts, message in records:
            row = SyncRecord.objects.filter(user=user, category=SyncCategory.DAILY_LOG, reference=reference).first()
            payload = {
                **base_payload,
                "reference": reference,
                "demo_fixture": True,
                "queue_status_hint": reference.replace("demo-offline-", ""),
            }
            if row is None:
                SyncRecord.objects.create(
                    user=user,
                    farm=farm,
                    category=SyncCategory.DAILY_LOG,
                    reference=reference,
                    status=status,
                    attempt_count=attempts,
                    last_attempt_at=timezone.now() - timedelta(minutes=5) if attempts else None,
                    last_error_message=message,
                    payload=payload,
                    log_date=timezone.localdate(),
                )
            else:
                row.farm = farm
                row.status = status
                row.attempt_count = attempts
                row.last_attempt_at = timezone.now() - timedelta(minutes=5) if attempts else None
                row.last_error_message = message
                row.payload = payload
                row.log_date = timezone.localdate()
                row.save()

        dlq = SyncConflictDLQ.objects.filter(idempotency_key="demo-dead-letter-retryable").first()
        if dlq is None:
            SyncConflictDLQ.objects.create(
                farm=farm,
                actor=user,
                conflict_type="VALIDATION_FAILURE",
                conflict_reason="Demo retryable offline DailyLog validation failure.",
                endpoint="/api/v1/offline/daily-log-replay/atomic/",
                http_method="POST",
                request_payload={**base_payload, "demo_fixture": "dead_letter"},
                idempotency_key="demo-dead-letter-retryable",
                device_timestamp=timezone.now() - timedelta(hours=1),
                status="PENDING",
            )
        else:
            dlq.status = "PENDING"
            dlq.conflict_reason = "Demo retryable offline DailyLog validation failure."
            dlq.request_payload = {**base_payload, "demo_fixture": "dead_letter"}
            dlq.deleted_at = None
            dlq.is_active = True
            dlq.save(update_fields=["status", "conflict_reason", "request_payload", "deleted_at", "is_active", "updated_at"])

        quarantine = OfflineSyncQuarantine.objects.filter(idempotency_key="demo-mode-switch-quarantine").first()
        if quarantine is None:
            OfflineSyncQuarantine.objects.create(
                farm=farm,
                submitted_by=user,
                variance_type="MODE_SWITCH_QUARANTINE",
                device_timestamp=timezone.now() - timedelta(hours=2),
                original_payload={**base_payload, "demo_fixture": "mode_switch_quarantine"},
                idempotency_key="demo-mode-switch-quarantine",
                status="PENDING_REVIEW",
            )
        else:
            quarantine.status = "PENDING_REVIEW"
            quarantine.original_payload = {**base_payload, "demo_fixture": "mode_switch_quarantine"}
            quarantine.deleted_at = None
            quarantine.is_active = True
            quarantine.save(update_fields=["status", "original_payload", "deleted_at", "is_active", "updated_at"])

        return {
            "sync_records": SyncRecord.objects.filter(user=user, category=SyncCategory.DAILY_LOG, reference__startswith="demo-offline-").count(),
            "dlq": SyncConflictDLQ.objects.filter(farm=farm, idempotency_key="demo-dead-letter-retryable").count(),
            "quarantine": OfflineSyncQuarantine.objects.filter(farm=farm, idempotency_key="demo-mode-switch-quarantine").count(),
        }

    def _reset_demo_evidence(self, *, farm, user):
        SyncRecord.objects.filter(user=user, category=SyncCategory.DAILY_LOG, reference__startswith="demo-offline-").delete()
        SyncConflictDLQ.objects.filter(farm=farm, idempotency_key__in=["demo-dead-letter-retryable"]).delete()
        OfflineSyncQuarantine.objects.filter(farm=farm, idempotency_key__in=["demo-mode-switch-quarantine"]).delete()
