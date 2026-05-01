import calendar
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from smart_agri.core.models import AuditLog
from smart_agri.core.models.farm import Farm
from smart_agri.finance.models import FiscalPeriod, FiscalYear
from smart_agri.finance.services.fiscal_governance_service import FiscalGovernanceService


class Command(BaseCommand):
    help = (
        "Ensure a fiscal year exists, backfill all missing monthly periods, "
        "and optionally reopen closed year/periods under governed audit."
    )

    def add_arguments(self, parser):
        parser.add_argument("--farm", required=True, help="Farm id, slug, or exact name")
        parser.add_argument("--year", required=True, type=int, help="Fiscal year, for example 2026")
        parser.add_argument(
            "--reopen-closed",
            action="store_true",
            help="Reopen closed fiscal year metadata and closed periods when encountered.",
        )
        parser.add_argument(
            "--reason",
            default="Operational fiscal maintenance",
            help="Audit reason used when reopening closed periods or fiscal year metadata.",
        )
        parser.add_argument(
            "--actor-username",
            default="",
            help="Username used for governed reopen actions and audit attribution.",
        )

    def handle(self, *args, **options):
        farm = self._resolve_farm(options["farm"])
        year = int(options["year"])
        reopen_closed = bool(options["reopen_closed"])
        reason = str(options["reason"] or "").strip() or "Operational fiscal maintenance"
        actor = self._resolve_actor(options.get("actor_username", ""))

        with transaction.atomic():
            fiscal_year, _ = FiscalYear.objects.get_or_create(
                farm=farm,
                year=year,
                defaults={
                    "start_date": date(year, 1, 1),
                    "end_date": date(year, 12, 31),
                    "is_closed": False,
                },
            )

            created_periods = 0
            reopened_periods = 0
            touched_periods = []

            if fiscal_year.is_closed:
                if not reopen_closed:
                    raise CommandError(
                        f"Fiscal year {year} for farm {farm.slug} is closed. "
                        "Re-run with --reopen-closed to reopen it."
                    )
                self._ensure_actor(actor, "reopen a closed fiscal year")
                fiscal_year.is_closed = False
                fiscal_year.save(update_fields=["is_closed"])
                AuditLog.objects.create(
                    actor=actor,
                    action="FISCAL_YEAR_REOPEN",
                    model="FiscalYear",
                    object_id=str(fiscal_year.id),
                    farm=farm,
                    new_payload={
                        "fiscal_year_id": fiscal_year.id,
                        "year": fiscal_year.year,
                        "status": "open",
                    },
                    reason=reason,
                )

            for month in range(1, 13):
                start_date = date(year, month, 1)
                _, last_day = calendar.monthrange(year, month)
                end_date = date(year, month, last_day)
                period, was_created = FiscalPeriod.objects.get_or_create(
                    fiscal_year=fiscal_year,
                    month=month,
                    defaults={
                        "start_date": start_date,
                        "end_date": end_date,
                        "status": FiscalPeriod.STATUS_OPEN,
                        "is_closed": False,
                    },
                )
                if was_created:
                    created_periods += 1
                    touched_periods.append(month)
                    continue

                normalized_status = FiscalPeriod._normalize_status(period.status)
                if normalized_status != FiscalPeriod.STATUS_OPEN:
                    if not reopen_closed:
                        raise CommandError(
                            f"Fiscal period {year}-{month:02d} is {normalized_status}. "
                            "Re-run with --reopen-closed to reopen closed periods."
                        )
                    self._ensure_actor(actor, "reopen a closed fiscal period")
                    FiscalGovernanceService.reopen_period(
                        period_id=period.id,
                        user=actor,
                        reason=reason,
                    )
                    reopened_periods += 1
                    touched_periods.append(month)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Fiscal year {year} for farm {farm.slug} is ready. "
                    f"created_periods={created_periods} reopened_periods={reopened_periods} "
                    f"months={','.join(str(month) for month in touched_periods) or 'none'}"
                )
            )

    def _resolve_farm(self, farm_ref):
        farm_ref = str(farm_ref).strip()
        queryset = Farm.objects.all()
        if farm_ref.isdigit():
            farm = queryset.filter(id=int(farm_ref)).first()
            if farm:
                return farm
        farm = queryset.filter(slug=farm_ref).first()
        if farm:
            return farm
        farm = queryset.filter(name=farm_ref).first()
        if farm:
            return farm
        raise CommandError(f"Farm not found for reference: {farm_ref}")

    def _resolve_actor(self, username):
        username = str(username or "").strip()
        user_model = get_user_model()
        if username:
            actor = user_model.objects.filter(username=username).first()
            if actor is None:
                raise CommandError(f"Actor username not found: {username}")
            return actor
        return user_model.objects.filter(is_superuser=True).order_by("id").first()

    def _ensure_actor(self, actor, action_label):
        if actor is None:
            raise CommandError(
                f"Unable to {action_label}: no superuser was found. "
                "Provide --actor-username explicitly."
            )
