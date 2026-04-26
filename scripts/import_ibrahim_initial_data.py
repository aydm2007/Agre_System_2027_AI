import os
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
sys.path.append(BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import Group, User  # noqa: E402
from django.db import IntegrityError, connection, transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from smart_agri.accounts.models import FarmMembership  # noqa: E402
from smart_agri.core.models.activity import Activity  # noqa: E402
from smart_agri.core.models.crop import Crop  # noqa: E402
from smart_agri.core.models.farm import Asset, Farm, Location, LocationWell  # noqa: E402
from smart_agri.core.models.log import DailyLog  # noqa: E402
from smart_agri.core.models.planning import Season  # noqa: E402
from smart_agri.core.models.settings import LaborRate, MachineRate, Supervisor, Uom  # noqa: E402
from smart_agri.core.models.task import Task  # noqa: E402
from smart_agri.core.models.tree import TreeLossReason, TreeProductivityStatus  # noqa: E402
from smart_agri.inventory.models import Unit, UnitConversion  # noqa: E402


@dataclass
class SourceConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    user: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "")
    dbname: str = "Ibrahim_DB"


def _src_conn():
    cfg = SourceConfig()
    return psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        dbname=cfg.dbname,
        cursor_factory=RealDictCursor,
    )


def _fetch_all(cur, sql: str):
    cur.execute(sql)
    return cur.fetchall()


def _exec(sql: str, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])


def _fk_columns_referencing(parent_table: str):
    query = """
    SELECT
      con.conrelid::regclass::text AS child_table,
      att2.attname AS child_column
    FROM pg_constraint con
    JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS cols(attnum, ord) ON TRUE
    JOIN LATERAL unnest(con.confkey) WITH ORDINALITY AS refcols(attnum, ord) ON cols.ord = refcols.ord
    JOIN pg_attribute att2 ON att2.attrelid = con.conrelid AND att2.attnum = cols.attnum
    WHERE con.contype = 'f'
      AND con.confrelid = %s::regclass
    """
    with connection.cursor() as cur:
        cur.execute(query, [parent_table])
        return cur.fetchall()


def _repoint_references(parent_table: str, old_id: int, new_id: int):
    for child_table, child_column in _fk_columns_referencing(parent_table):
        if child_table == "core_financialledger":
            # Ledger rows are immutable by doctrine.
            continue
        try:
            with transaction.atomic():
                with connection.cursor() as cur:
                    cur.execute(
                        sql.SQL("UPDATE {} SET {} = %s WHERE {} = %s").format(
                            sql.Identifier(child_table),
                            sql.Identifier(child_column),
                            sql.Identifier(child_column),
                        ),
                        [new_id, old_id],
                    )
        except IntegrityError:
            # If unique constraints block merging (1:1 style links), drop old side rows.
            with transaction.atomic():
                with connection.cursor() as cur:
                    cur.execute(
                        sql.SQL("DELETE FROM {} WHERE {} = %s").format(
                            sql.Identifier(child_table),
                            sql.Identifier(child_column),
                        ),
                        [old_id],
                    )


def _hard_delete_by_id(table: str, row_id: int):
    with connection.cursor() as cur:
        cur.execute(
            sql.SQL("DELETE FROM {} WHERE id = %s").format(sql.Identifier(table)),
            [row_id],
        )


def import_users_and_access(cur):
    users = _fetch_all(
        cur,
        """
        SELECT id, password, last_login, is_superuser, username, first_name, last_name,
               email, is_staff, is_active, date_joined
        FROM auth_user
        ORDER BY id
        """,
    )
    groups = _fetch_all(cur, "SELECT id, name FROM auth_group ORDER BY id")
    user_groups = _fetch_all(cur, "SELECT user_id, group_id FROM auth_user_groups")
    user_perms = _fetch_all(cur, "SELECT user_id, permission_id FROM auth_user_user_permissions")
    group_perms = _fetch_all(cur, "SELECT group_id, permission_id FROM auth_group_permissions")

    for g in groups:
        Group.objects.update_or_create(id=g["id"], defaults={"name": g["name"]})

    for u in users:
        defaults = {
            "password": u["password"],
            "last_login": u["last_login"],
            "is_superuser": u["is_superuser"],
            "username": u["username"],
            "first_name": u["first_name"],
            "last_name": u["last_name"],
            "email": u["email"],
            "is_staff": u["is_staff"],
            "is_active": u["is_active"],
            "date_joined": u["date_joined"],
        }
        User.objects.update_or_create(id=u["id"], defaults=defaults)

    ug_table = User.groups.through._meta.db_table
    up_table = User.user_permissions.through._meta.db_table
    gp_table = Group.permissions.through._meta.db_table

    for rel in user_groups:
        _exec(
            f"INSERT INTO {ug_table} (user_id, group_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            [rel["user_id"], rel["group_id"]],
        )
    for rel in user_perms:
        _exec(
            f"INSERT INTO {up_table} (user_id, permission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            [rel["user_id"], rel["permission_id"]],
        )
    for rel in group_perms:
        _exec(
            f"INSERT INTO {gp_table} (group_id, permission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            [rel["group_id"], rel["permission_id"]],
        )

    return {
        "users": len(users),
        "groups": len(groups),
        "user_groups": len(user_groups),
        "user_permissions": len(user_perms),
        "group_permissions": len(group_perms),
    }


def import_reference_data(cur):
    seasons = _fetch_all(
        cur,
        "SELECT id, name, start_date, end_date, is_active, description FROM core_season ORDER BY id",
    )
    units = _fetch_all(
        cur,
        """
        SELECT id, code, name, symbol, category, precision, metadata
        FROM core_unit
        ORDER BY id
        """,
    )
    conversions = _fetch_all(
        cur,
        "SELECT id, from_unit_id, to_unit_id, multiplier FROM core_unitconversion ORDER BY id",
    )
    uoms = _fetch_all(
        cur,
        "SELECT code, name, category, is_base, to_base_factor, decimals FROM core_uom ORDER BY code",
    )
    loss_reasons = _fetch_all(
        cur,
        "SELECT id, code, name_en, name_ar, description FROM core_treelossreason ORDER BY id",
    )
    productivity = _fetch_all(
        cur,
        """
        SELECT id, code, name_en, name_ar, description
        FROM core_treeproductivitystatus
        ORDER BY id
        """,
    )

    for s in seasons:
        Season.objects.update_or_create(
            id=s["id"],
            defaults={
                "name": s["name"],
                "start_date": s["start_date"],
                "end_date": s["end_date"],
                "is_active": s["is_active"],
                "description": s["description"] or "",
            },
        )

    for u in units:
        Unit.objects.update_or_create(
            id=u["id"],
            defaults={
                "code": u["code"],
                "name": u["name"],
                "symbol": u["symbol"] or "",
                "category": u["category"] or Unit.CATEGORY_OTHER,
                "precision": u["precision"] if u["precision"] is not None else 3,
                "metadata": u["metadata"] or {},
            },
        )

    for c in conversions:
        if not Unit.objects.filter(id=c["from_unit_id"]).exists():
            continue
        if not Unit.objects.filter(id=c["to_unit_id"]).exists():
            continue
        UnitConversion.objects.update_or_create(
            id=c["id"],
            defaults={
                "from_unit_id": c["from_unit_id"],
                "to_unit_id": c["to_unit_id"],
                "multiplier": c["multiplier"],
            },
        )

    for u in uoms:
        Uom.objects.update_or_create(
            code=u["code"],
            defaults={
                "name": u["name"],
                "category": u["category"],
                "is_base": u["is_base"],
                "to_base_factor": u["to_base_factor"],
                "decimals": u["decimals"],
            },
        )

    for r in loss_reasons:
        TreeLossReason.objects.update_or_create(
            id=r["id"],
            defaults={
                "code": r["code"],
                "name_en": r["name_en"],
                "name_ar": r["name_ar"],
                "description": r["description"] or "",
            },
        )

    for p in productivity:
        TreeProductivityStatus.objects.update_or_create(
            id=p["id"],
            defaults={
                "code": p["code"],
                "name_en": p["name_en"],
                "name_ar": p["name_ar"],
                "description": p["description"] or "",
            },
        )

    return {
        "seasons": len(seasons),
        "units": len(units),
        "unit_conversions": len(conversions),
        "uoms": len(uoms),
        "tree_loss_reasons": len(loss_reasons),
        "tree_productivity_statuses": len(productivity),
    }


def cleanup_english_seed_data():
    crop_map = {
        "Mango": "مانجو قديم",
        "Banana": "موز قديم",
        "Wheat": "قمح قديم",
        "Tomato": "طماطم قديم",
        "Potato": "بطاطس قديم",
    }
    location_map = {
        "Field A": "الحقل أ قديم",
        "Field B": "الحقل ب قديم",
        "Service Yard": "ساحة الخدمات قديم",
    }
    asset_map = {
        "Main Well": "البئر الرئيسي قديم",
        "Main Tractor": "الجرار الرئيسي قديم",
        "Irrigation Pump": "مضخة الري قديم",
    }
    task_map = {
        "Planting Operation": ("عملية الزراعة قديم", "الزراعة"),
        "Irrigation Operation": ("عملية الري قديم", "الري"),
        "Harvest Operation": ("عملية الحصاد قديم", "الحصاد"),
    }

    updated = {
        "crops": 0,
        "locations": 0,
        "assets": 0,
        "tasks": 0,
        "daily_logs": 0,
    }

    for en_name, ar_name in crop_map.items():
        updated["crops"] += Crop._base_manager.filter(name=en_name).update(name=ar_name)

    for en_name, ar_name in location_map.items():
        updated["locations"] += Location._base_manager.filter(name=en_name).update(name=ar_name)

    for en_name, ar_name in asset_map.items():
        updated["assets"] += Asset._base_manager.filter(name=en_name).update(name=ar_name)

    for en_name, (ar_name, ar_stage) in task_map.items():
        updated["tasks"] += Task._base_manager.filter(name=en_name).update(name=ar_name, stage=ar_stage)

    updated["daily_logs"] = DailyLog._base_manager.filter(notes="Initial seeded log").update(
        notes="سجل إدخال أولي قديم"
    )

    return updated


def finalize_legacy_old_cleanup():
    summary = {
        "crop_merged_deleted": 0,
        "location_merged_deleted": 0,
        "asset_merged_deleted": 0,
        "task_merged_deleted": 0,
        "daily_logs_notes_updated": 0,
    }

    crop_old = Crop._base_manager.filter(name__contains="قديم")
    for old in crop_old:
        base_name = old.name.replace("قديم", "").strip()
        target = Crop._base_manager.filter(name=base_name).exclude(id=old.id).order_by("id").first()
        if target:
            _repoint_references("core_crop", old.id, target.id)
            _hard_delete_by_id("core_crop", old.id)
            summary["crop_merged_deleted"] += 1

    location_old = Location._base_manager.filter(name__contains="قديم")
    for old in location_old:
        base_name = old.name.replace("قديم", "").strip()
        target = (
            Location._base_manager.filter(name=base_name, farm_id=old.farm_id)
            .exclude(id=old.id)
            .order_by("id")
            .first()
        )
        if target:
            _repoint_references("core_location", old.id, target.id)
            _hard_delete_by_id("core_location", old.id)
            summary["location_merged_deleted"] += 1

    asset_old = Asset._base_manager.filter(name__contains="قديم")
    for old in asset_old:
        base_name = old.name.replace("قديم", "").strip()
        target = (
            Asset._base_manager.filter(name=base_name, farm_id=old.farm_id)
            .exclude(id=old.id)
            .order_by("id")
            .first()
        )
        if target:
            _repoint_references("core_asset", old.id, target.id)
            _hard_delete_by_id("core_asset", old.id)
            summary["asset_merged_deleted"] += 1

    task_old = Task._base_manager.filter(name__contains="قديم")
    for old in task_old:
        base_name = old.name.replace("قديم", "").strip()
        target = (
            Task._base_manager.filter(name=base_name, crop_id=old.crop_id, stage=old.stage)
            .exclude(id=old.id)
            .order_by("id")
            .first()
        )
        if target:
            _repoint_references("core_task", old.id, target.id)
            _hard_delete_by_id("core_task", old.id)
            summary["task_merged_deleted"] += 1

    summary["daily_logs_notes_updated"] = DailyLog._base_manager.filter(notes__contains="قديم").update(
        notes="سجل إدخال أولي"
    )

    return summary


def complete_initial_master_data():
    removed_english = cleanup_english_seed_data()

    farm_specs = [
        ("سردود", "sardud", "الحديدة", Farm.ZAKAT_TITHE),
        ("الجرابة", "al-jarubah", "إب", Farm.ZAKAT_HALF_TITHE),
    ]
    crop_specs = [
        ("مانجو", "Open", True),
        ("موز", "Open", True),
        ("قمح", "Open", False),
        ("طماطم", "Protected", False),
        ("بطاطس", "Open", False),
    ]

    admin = User.objects.filter(is_superuser=True).order_by("id").first() or User.objects.order_by("id").first()
    if admin is None:
        admin = User.objects.create_superuser("admin", "admin@example.com", "123456")

    farms = []
    for name, slug, region, zakat_rule in farm_specs:
        farm, _ = Farm.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "region": region, "zakat_rule": zakat_rule},
        )
        farms.append(farm)
        FarmMembership.objects.get_or_create(user=admin, farm=farm, defaults={"role": "Admin"})

    for name, mode, perennial in crop_specs:
        Crop.objects.get_or_create(
            name=name,
            mode=mode,
            defaults={"is_perennial": perennial, "max_yield_per_ha": Decimal("0.000")},
        )

    if not Season.objects.exists():
        Season.objects.create(
            name=f"شتاء {date.today().year}",
            start_date=date(date.today().year, 1, 1),
            end_date=date(date.today().year, 3, 31),
            is_active=True,
        )
        Season.objects.create(
            name=f"صيف {date.today().year}",
            start_date=date(date.today().year, 4, 1),
            end_date=date(date.today().year, 9, 30),
            is_active=True,
        )

    created_assets = 0
    for farm in farms:
        field_a, _ = Location.objects.get_or_create(farm=farm, name="الحقل أ", defaults={"type": "Field"})
        field_b, _ = Location.objects.get_or_create(farm=farm, name="الحقل ب", defaults={"type": "Field"})
        service_loc, _ = Location.objects.get_or_create(
            farm=farm,
            name="ساحة الخدمات",
            defaults={"type": "Service"},
        )

        well_asset, created = Asset.objects.get_or_create(
            farm=farm,
            name="البئر الرئيسي",
            defaults={
                "category": "بئر",
                "asset_type": "well",
                "purchase_value": Decimal("150000.00"),
                "status": "active",
            },
        )
        created_assets += int(created)

        tractor, created = Asset.objects.get_or_create(
            farm=farm,
            name="الجرار الرئيسي",
            defaults={
                "category": "معدات",
                "asset_type": "tractor",
                "purchase_value": Decimal("350000.00"),
                "status": "active",
            },
        )
        created_assets += int(created)

        pump, created = Asset.objects.get_or_create(
            farm=farm,
            name="مضخة الري",
            defaults={
                "category": "ري",
                "asset_type": "pump",
                "purchase_value": Decimal("120000.00"),
                "status": "active",
            },
        )
        created_assets += int(created)

        LocationWell.objects.get_or_create(
            location=field_a,
            asset=well_asset,
            defaults={
                "well_depth": Decimal("95.00"),
                "pump_type": "غمّاسة",
                "capacity_lps": Decimal("18.50"),
                "status": "active",
                "is_operational": True,
            },
        )

        LaborRate.objects.get_or_create(
            farm=farm,
            role_name="عامل يومي",
            effective_date=timezone.localdate(),
            defaults={
                "daily_rate": Decimal("8000.0000"),
                "cost_per_hour": Decimal("1000.0000"),
                "currency": "YER",
            },
        )

        MachineRate.objects.get_or_create(
            asset=tractor,
            defaults={
                "daily_rate": Decimal("25000.0000"),
                "cost_per_hour": Decimal("3000.0000"),
                "fuel_consumption_rate": Decimal("5.0000"),
                "currency": "YER",
            },
        )
        MachineRate.objects.get_or_create(
            asset=pump,
            defaults={
                "daily_rate": Decimal("12000.0000"),
                "cost_per_hour": Decimal("1500.0000"),
                "fuel_consumption_rate": Decimal("2.5000"),
                "currency": "YER",
            },
        )

        supervisor, _ = Supervisor.objects.get_or_create(
            farm=farm,
            code=f"SUP-{farm.slug.upper()}",
            defaults={"name": f"مشرف {farm.name}"},
        )

        sample_crop = Crop.objects.order_by("id").first()
        if sample_crop:
            plant_task, _ = Task.objects.get_or_create(
                crop=sample_crop,
                stage="الزراعة",
                name="عملية الزراعة",
                defaults={"requires_area": True},
            )

            Task.objects.get_or_create(
                crop=sample_crop,
                stage="الري",
                name="عملية الري",
                defaults={"requires_well": True, "target_asset_type": Task.AssetType.WELL},
            )

            Task.objects.get_or_create(
                crop=sample_crop,
                stage="الحصاد",
                name="عملية الحصاد",
                defaults={"is_harvest_task": True},
            )

            log, _ = DailyLog.objects.get_or_create(
                farm=farm,
                log_date=timezone.localdate(),
                defaults={
                    "supervisor": supervisor,
                    "status": DailyLog.STATUS_DRAFT,
                    "created_by": admin,
                    "updated_by": admin,
                    "notes": "سجل إدخال أولي",
                },
            )

            Activity.objects.get_or_create(
                log=log,
                crop=sample_crop,
                task=plant_task,
                location=field_b or service_loc,
                defaults={
                    "created_by": admin,
                    "updated_by": admin,
                    "days_spent": Decimal("1.00"),
                    "cost_total": Decimal("0.0000"),
                },
            )

    final_cleanup = finalize_legacy_old_cleanup()

    return {
        "deleted_english_seed": removed_english,
        "final_cleanup": final_cleanup,
        "farms": Farm.objects.count(),
        "farm_memberships": FarmMembership.objects.count(),
        "crops": Crop.objects.count(),
        "seasons": Season.objects.count(),
        "locations": Location.objects.count(),
        "assets": Asset.objects.count(),
        "location_wells": LocationWell.objects.count(),
        "tasks": Task.objects.count(),
        "daily_logs": DailyLog.objects.count(),
        "activities": Activity.objects.count(),
        "labor_rates": LaborRate.objects.count(),
        "machine_rates": MachineRate.objects.count(),
        "users": User.objects.count(),
        "groups": Group.objects.count(),
        "created_assets_this_run": created_assets,
    }


def main():
    print("=== Ibrahim_DB Initial Data Import & Completion ===")
    with _src_conn() as src, src.cursor() as cur, transaction.atomic():
        access_stats = import_users_and_access(cur)
        ref_stats = import_reference_data(cur)
        completion_stats = complete_initial_master_data()

    print("Import from Ibrahim_DB:")
    for k, v in access_stats.items():
        print(f"  - {k}: {v}")
    for k, v in ref_stats.items():
        print(f"  - {k}: {v}")

    print("Current Initial Data Totals:")
    for k, v in completion_stats.items():
        print(f"  - {k}: {v}")

    print("=== DONE ===")


if __name__ == "__main__":
    main()
