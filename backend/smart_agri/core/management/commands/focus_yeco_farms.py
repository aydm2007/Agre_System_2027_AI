from datetime import date
from decimal import Decimal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.utils import timezone

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import (
    Activity,
    ActivityEmployee,
    ActivityItem,
    ActivityMaterialApplication,
    Crop,
    CropVariety,
    DailyLog,
    Employee,
    Farm,
    Location,
    Task,
)
from smart_agri.core.services.inventory_service import InventoryService
from smart_agri.finance.models import FinancialLedger, FiscalPeriod, FiscalYear
from smart_agri.inventory.models import Item, ItemInventory, Unit
from smart_agri.sales.models import Customer
from smart_agri.sales.services import SaleService

User = get_user_model()


class Command(BaseCommand):
    help = (
        "YECO focus command: keep only the Sardud model farm operational scope, "
        "archive other farms, and seed Sardud Arabic operational E2E cycle."
    )

    TARGET_FARMS = (
        ("مزرعة سردود النموذجية", "sardud", "الحديدة"),
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply-cleanup", action="store_true")
        parser.add_argument("--seed-sardud-cycle", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        apply_cleanup = bool(options["apply_cleanup"])
        seed_cycle = bool(options["seed_sardud_cycle"])
        dry_run = bool(options["dry_run"])

        if not apply_cleanup and not seed_cycle:
            raise SystemExit("حدد على الأقل: --apply-cleanup أو --seed-sardud-cycle")

        with transaction.atomic():
            target_farms = self._ensure_target_farms()
            if apply_cleanup:
                self._cleanup_non_target_farms(target_farms=target_farms, dry_run=dry_run)
            if seed_cycle:
                self._seed_sardud_cycle(target_farms=target_farms, dry_run=dry_run)

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("DRY-RUN: تم التراجع عن كل التغييرات."))

    def _ensure_target_farms(self):
        created = 0
        result = {}
        for name, slug, region in self.TARGET_FARMS:
            farm, was_created = Farm._base_manager.get_or_create(
                slug=slug,
                defaults={"name": name, "region": region},
            )
            if was_created:
                created += 1
            if farm.deleted_at is not None or not farm.is_active:
                farm.deleted_at = None
                farm.is_active = True
            if farm.name != name or farm.region != region:
                farm.name = name
                farm.region = region
            farm.save(update_fields=["name", "region", "deleted_at", "is_active", "updated_at"])
            result[slug] = farm
        self.stdout.write(
            self.style.SUCCESS(f"Target farms ready: {len(result)} (created={created}).")
        )
        return result

    def _cleanup_non_target_farms(self, *, target_farms, dry_run):
        keep_ids = [farm.id for farm in target_farms.values()]
        now = timezone.now()

        obsolete_qs = Farm._base_manager.filter(deleted_at__isnull=True).exclude(id__in=keep_ids)
        obsolete_ids = list(obsolete_qs.values_list("id", flat=True))
        self.stdout.write(f"Farms to archive: {len(obsolete_ids)}")
        if not obsolete_ids:
            return

        # Revoke memberships to non-target farms.
        membership_count = FarmMembership.objects.filter(farm_id__in=obsolete_ids).count()
        if not dry_run:
            FarmMembership.objects.filter(farm_id__in=obsolete_ids).delete()
        self.stdout.write(f"Memberships removed: {membership_count}")

        # Soft archive farm-scoped models generically where possible.
        archived_rows = 0
        skipped_models = []
        for model in apps.get_models():
            field_names = {f.name for f in model._meta.get_fields()}
            if "farm" not in field_names:
                continue
            if not hasattr(model, "_base_manager"):
                continue
            qs = model._base_manager.filter(farm_id__in=obsolete_ids)
            count = qs.count()
            if count == 0:
                continue

            has_deleted = "deleted_at" in field_names
            has_active = "is_active" in field_names
            if has_deleted or has_active:
                update_kwargs = {}
                if has_deleted:
                    update_kwargs["deleted_at"] = now
                if has_active:
                    update_kwargs["is_active"] = False
                if not dry_run:
                    qs.update(**update_kwargs)
                archived_rows += count
            else:
                # Keep immutable/non-soft tables untouched; they remain historically traceable.
                skipped_models.append((model._meta.label, count))

        if not dry_run:
            obsolete_qs.update(deleted_at=now, is_active=False)

        self.stdout.write(self.style.SUCCESS(f"Archived rows (soft): {archived_rows}"))
        if skipped_models:
            self.stdout.write("Skipped non-soft models (kept as history):")
            for label, count in skipped_models:
                self.stdout.write(f" - {label}: {count}")

    def _seed_sardud_cycle(self, *, target_farms, dry_run):
        sardud = target_farms["sardud"]
        self._sync_sequences_for_seed()

        manager = self._ensure_user("sardud_manager", "Manager", "سردود")
        sales_user = self._ensure_user("sardud_sales", "Sales", "سردود")
        approver_user = self._ensure_user("sardud_finance", "Finance", "سردود")
        for usr, role in ((manager, "Admin"), (sales_user, "DataEntry"), (approver_user, "Manager")):
            FarmMembership.objects.get_or_create(user=usr, farm=sardud, defaults={"role": role})

        store, _ = Location._base_manager.get_or_create(
            farm=sardud, name="مستودع سردود", defaults={"type": "Service", "code": "SD-STORE"}
        )
        field, _ = Location._base_manager.get_or_create(
            farm=sardud, name="حقل سردود 1", defaults={"type": "Field", "code": "SD-F1"}
        )

        kg, _ = Unit._base_manager.get_or_create(code="KG", defaults={"name": "كيلوجرام", "symbol": "kg", "category": "mass"})
        liter, _ = Unit._base_manager.get_or_create(code="L", defaults={"name": "لتر", "symbol": "L", "category": "volume"})

        crop, _ = Crop._base_manager.get_or_create(name="الذرة البيضاء", defaults={"max_yield_per_ha": Decimal("7.0")})
        variety, _ = CropVariety._base_manager.get_or_create(crop=crop, name="الذرة البيضاء - صنف محلي")
        task_fert, _ = Task._base_manager.get_or_create(crop=crop, name="تسميد الذرة", defaults={"stage": "الرعاية"})
        task_harvest, _ = Task._base_manager.get_or_create(
            crop=crop, name="حصاد الذرة", defaults={"stage": "الحصاد", "is_harvest_task": True}
        )

        worker_1, _ = Employee._base_manager.get_or_create(
            farm=sardud,
            employee_id="SD-W-001",
            defaults={
                "first_name": "محمد",
                "last_name": "السروري",
                "role": Employee.TYPE_WORKER,
                "category": "CASUAL",
                "payment_mode": "SURRA",
                "shift_rate": Decimal("6000.0000"),
                "base_salary": Decimal("0.0000"),
            },
        )
        worker_2, _ = Employee._base_manager.get_or_create(
            farm=sardud,
            employee_id="SD-W-002",
            defaults={
                "first_name": "عبدالله",
                "last_name": "المتوكل",
                "role": Employee.TYPE_WORKER,
                "category": "CASUAL",
                "payment_mode": "SURRA",
                "shift_rate": Decimal("5500.0000"),
                "base_salary": Decimal("0.0000"),
            },
        )

        diesel, _ = Item._base_manager.get_or_create(
            name="ديزل - سردود",
            defaults={"group": "Fuel", "uom": "L", "unit": liter, "unit_price": Decimal("1150.00")},
        )
        urea, _ = Item._base_manager.get_or_create(
            name="سماد يوريا 46% - سردود",
            defaults={"group": "Fertilizers", "uom": "kg", "unit": kg, "unit_price": Decimal("145.00")},
        )
        maize_product, _ = Item._base_manager.get_or_create(
            name="ذرة بيضاء - محصول سردود",
            defaults={"group": "Harvest", "uom": "kg", "unit": kg, "unit_price": Decimal("230.00")},
        )

        today = timezone.localdate()
        self._ensure_open_period(sardud, today)

        # Inventory inflow and field transfer
        InventoryService.process_grn(
            farm=sardud,
            item=urea,
            location=store,
            qty=Decimal("1000"),
            unit_cost=Decimal("140.00"),
            ref_id=f"GRN-SD-UREA-{today.isoformat()}",
            actor_user=manager,
        )
        InventoryService.process_grn(
            farm=sardud,
            item=diesel,
            location=store,
            qty=Decimal("2000"),
            unit_cost=Decimal("1100.00"),
            ref_id=f"GRN-SD-DIESEL-{today.isoformat()}",
            actor_user=manager,
        )
        InventoryService.transfer_stock(
            farm=sardud,
            item=urea,
            from_loc=store,
            to_loc=field,
            qty=Decimal("300"),
            user=manager,
        )
        InventoryService.process_grn(
            farm=sardud,
            item=maize_product,
            location=store,
            qty=Decimal("800"),
            unit_cost=Decimal("180.00"),
            ref_id=f"HARV-SD-MAIZE-{today.isoformat()}",
            actor_user=manager,
        )

        # Arabic daily operational logs
        daily_log, _ = DailyLog._base_manager.get_or_create(
            farm=sardud,
            log_date=today,
            defaults={
                "notes": "تنفيذ دورة تشغيل سردود: تسميد، متابعة ري، وتجهيز تسليم إنتاج.",
                "created_by": manager,
                "updated_by": manager,
                "status": DailyLog.STATUS_SUBMITTED,
                "variance_status": "OK",
            },
        )
        activity = Activity._base_manager.create(
            log=daily_log,
            crop=crop,
            crop_variety=variety,
            task=task_fert,
            location=field,
            created_by=manager,
            updated_by=manager,
            days_spent=Decimal("1.00"),
            agreed_daily_rate=Decimal("5800.00"),
            data={"note": "تسميد الذرة في حقل سردود 1 وفق الخطة اليومية."},
        )
        ActivityMaterialApplication.objects.update_or_create(
            activity=activity, defaults={"fertilizer_quantity": Decimal("40.000")}
        )
        ActivityItem._base_manager.update_or_create(
            activity=activity,
            item=urea,
            defaults={
                "qty": Decimal("40.000"),
                "uom": "kg",
                "cost_per_unit": Decimal("145.0000"),
                "total_cost": Decimal("5800.0000"),
            },
        )
        ActivityEmployee.objects.get_or_create(
            activity=activity,
            employee=worker_1,
            defaults={"surrah_share": Decimal("1.00"), "wage_cost": Decimal("6000.0000")},
        )
        ActivityEmployee.objects.get_or_create(
            activity=activity,
            employee=worker_2,
            defaults={"surrah_share": Decimal("0.50"), "wage_cost": Decimal("2750.0000")},
        )

        customer, _ = Customer._base_manager.get_or_create(name="عميل جملة - سوق سردود")
        invoice = SaleService.create_invoice(
            customer=customer,
            location=store,
            invoice_date=today,
            items_data=[{"item": maize_product.id, "qty": Decimal("250"), "unit_price": Decimal("260.00")}],
            user=sales_user,
            notes="بيع إنتاج الذرة البيضاء - سردود",
        )
        invoice = SaleService.confirm_sale(invoice=invoice, user=approver_user)

        store_maize = ItemInventory.objects.filter(farm=sardud, location=store, item=maize_product).first()
        field_urea = ItemInventory.objects.filter(farm=sardud, location=field, item=urea).first()
        revenue_lines = FinancialLedger.objects.filter(
            farm=sardud,
            account_code=FinancialLedger.ACCOUNT_SALES_REVENUE,
            description__icontains=f"#{invoice.id}",
        ).count()

        self.stdout.write(self.style.SUCCESS("Sardud cycle completed."))
        self.stdout.write(f" - DailyLog ID: {daily_log.id}")
        self.stdout.write(f" - Activity ID: {activity.id} ({task_fert.name})")
        self.stdout.write(f" - Invoice ID: {invoice.id}, status={invoice.status}")
        self.stdout.write(f" - Store maize qty: {store_maize.qty if store_maize else 'N/A'}")
        self.stdout.write(f" - Field urea qty: {field_urea.qty if field_urea else 'N/A'}")
        self.stdout.write(f" - Revenue ledger lines: {revenue_lines}")
        if not dry_run:
            if not store_maize or store_maize.qty < Decimal("550"):
                raise RuntimeError("E2E check failed: Sardud maize stock did not reconcile.")
            if revenue_lines == 0:
                raise RuntimeError("E2E check failed: no revenue ledger lines created for Sardud sale.")

    def _ensure_user(self, username, first_name, last_name):
        user = User.objects.filter(username=username).first()
        created = False
        if user is None:
            try:
                with transaction.atomic():
                    user = User.objects.create(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        is_active=True,
                    )
                created = True
            except IntegrityError:
                self._sync_pk_sequence(User)
                with transaction.atomic():
                    user = User.objects.create(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        is_active=True,
                    )
                created = True
        if created:
            user.set_password("AgriAsset2026!")
            user.save(update_fields=["password"])
        return user

    def _sync_pk_sequence(self, model):
        pk = model._meta.pk
        if pk.get_internal_type() not in {"AutoField", "BigAutoField", "SmallAutoField"}:
            return
        table = model._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 1),
                    true
                )
                """
            )

    def _sync_sequences_for_seed(self):
        models = [
            User,
            Farm,
            Location,
            Unit,
            Item,
            Crop,
            CropVariety,
            Task,
            Employee,
            DailyLog,
            Activity,
            Customer,
            FarmMembership,
            FiscalYear,
            FiscalPeriod,
        ]
        for model in models:
            self._sync_pk_sequence(model)

    def _ensure_open_period(self, farm, today):
        fy, _ = FiscalYear.objects.get_or_create(
            farm=farm,
            year=today.year,
            defaults={
                "start_date": date(today.year, 1, 1),
                "end_date": date(today.year, 12, 31),
                "is_closed": False,
            },
        )
        FiscalPeriod.objects.get_or_create(
            fiscal_year=fy,
            month=today.month,
            defaults={
                "start_date": date(today.year, today.month, 1),
                "end_date": date(today.year, today.month, 28),
                "is_closed": False,
                "status": "open",
            },
        )
