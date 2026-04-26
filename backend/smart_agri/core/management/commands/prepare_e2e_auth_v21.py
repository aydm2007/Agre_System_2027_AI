from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Farm
from smart_agri.core.models.settings import FarmSettings


PROOF_FARM_SLUG = "sardood-farm"
CANONICAL_PROOF_FARM_NAME = "\u0645\u0632\u0631\u0639\u0629 \u0633\u0631\u062f\u0648\u062f"


class Command(BaseCommand):
    help = "Ensure a deterministic E2E auth user exists for focused Playwright proofs."

    def _active_farm_by_slug(self) -> Farm | None:
        return Farm._base_manager.filter(slug=PROOF_FARM_SLUG, deleted_at__isnull=True).first()

    def _active_farm_by_name(self) -> Farm | None:
        return Farm._base_manager.filter(
            name=CANONICAL_PROOF_FARM_NAME,
            deleted_at__isnull=True,
        ).first()

    def _normalize_proof_farm_slug(self, farm: Farm) -> tuple[Farm, bool]:
        if farm.slug == PROOF_FARM_SLUG:
            return farm, False

        slug_taken = Farm._base_manager.filter(
            slug=PROOF_FARM_SLUG,
            deleted_at__isnull=True,
        ).exclude(pk=farm.pk).exists()
        if slug_taken:
            raise CommandError(f"proof_farm_slug_conflict={PROOF_FARM_SLUG}")

        farm.slug = PROOF_FARM_SLUG
        farm.save(update_fields=["slug"])
        return farm, True

    def _resolve_proof_farm(self) -> tuple[Farm, bool]:
        slug_farm = self._active_farm_by_slug()
        name_farm = self._active_farm_by_name()
        if slug_farm is not None and name_farm is not None and slug_farm.pk != name_farm.pk:
            raise CommandError(
                f"proof_farm_conflict=slug:{slug_farm.pk},name:{name_farm.pk}"
            )

        farm = slug_farm or name_farm
        if farm is None:
            call_command("seed_saradud_documentary_cycle")
            slug_farm = self._active_farm_by_slug()
            name_farm = self._active_farm_by_name()
            if slug_farm is not None and name_farm is not None and slug_farm.pk != name_farm.pk:
                raise CommandError(
                    f"proof_farm_conflict_after_seed=slug:{slug_farm.pk},name:{name_farm.pk}"
                )
            farm = slug_farm or name_farm

        if farm is None:
            raise CommandError(f"proof_farm_missing={PROOF_FARM_SLUG}")
        return self._normalize_proof_farm_slug(farm)

    def _ensure_proof_farm_ready(self) -> tuple[Farm, bool]:
        farm, slug_updated = self._resolve_proof_farm()

        settings, _ = FarmSettings.objects.get_or_create(farm=farm)
        visibility_updated = False
        if not settings.show_daily_log_smart_card:
            settings.show_daily_log_smart_card = True
            settings.save(update_fields=["show_daily_log_smart_card"])
            visibility_updated = True
        daily_log_context_updated = self._ensure_daily_log_proof_context(farm)
        return farm, slug_updated or visibility_updated or daily_log_context_updated

    def _ensure_plan_covers_today(self, plan, today):
        if plan.start_date and plan.end_date and plan.start_date <= today <= plan.end_date:
            return False

        plan.start_date = today.replace(month=1, day=1)
        plan.end_date = today.replace(month=12, day=31)
        plan.save(update_fields=["start_date", "end_date"])
        return True

    def _ensure_plan_locations(self, plan, farm):
        from smart_agri.core.models.farm import Location
        from smart_agri.core.models.planning import CropPlanLocation
        if plan.plan_locations.exists():
            return False

        location = Location.objects.filter(farm=farm, deleted_at__isnull=True).first()
        if location is None:
            location = Location.objects.create(
                farm=farm,
                name=f"حقل الاختبار E2E-{plan.id}",
                area=10.0
            )
        CropPlanLocation.objects.create(crop_plan=plan, location=location)
        return True

    def _ensure_task_for_crop(self, *, crop, name, stage, archetype, is_perennial):
        from smart_agri.core.models import Task

        task = (
            Task.objects.filter(crop=crop, deleted_at__isnull=True)
            .order_by("id")
            .first()
        )
        if task is not None:
            return False

        Task.objects.create(
            crop=crop,
            name=name,
            stage=stage,
            archetype=archetype,
            requires_tree_count=is_perennial,
            is_perennial_procedure=is_perennial,
            requires_area=not is_perennial,
        )
        return True

    def _ensure_daily_log_proof_context(self, farm: Farm) -> bool:
        from smart_agri.core.models import CropPlan, Task
        from smart_agri.core.models.crop import FarmCrop
        from smart_agri.core.models.task import Task as TaskModel

        today = timezone.localdate()
        updated = False
        active_plans = list(
            CropPlan.objects.filter(
                farm=farm,
                deleted_at__isnull=True,
                status__iexact="active",
            )
            .select_related("crop")
            .order_by("id")
        )

        perennial_plan = next(
            (plan for plan in active_plans if getattr(plan.crop, "is_perennial", False)),
            None,
        )
        seasonal_plan = next(
            (plan for plan in active_plans if not getattr(plan.crop, "is_perennial", False)),
            None,
        )

        if perennial_plan is None or seasonal_plan is None:
            call_command("seed_saradud_documentary_cycle")
            active_plans = list(
                CropPlan.objects.filter(
                    farm=farm,
                    deleted_at__isnull=True,
                    status__iexact="active",
                )
                .select_related("crop")
                .order_by("id")
            )
            perennial_plan = next(
                (plan for plan in active_plans if getattr(plan.crop, "is_perennial", False)),
                None,
            )
            seasonal_plan = next(
                (plan for plan in active_plans if not getattr(plan.crop, "is_perennial", False)),
                None,
            )

        if perennial_plan is None or seasonal_plan is None:
            raise CommandError("proof_farm_daily_log_context_missing=seasonal_or_perennial_plan")

        updated = self._ensure_plan_covers_today(perennial_plan, today) or updated
        updated = self._ensure_plan_covers_today(seasonal_plan, today) or updated

        updated = self._ensure_plan_locations(perennial_plan, farm) or updated
        updated = self._ensure_plan_locations(seasonal_plan, farm) or updated

        active_crop_ids = {plan.crop_id for plan in active_plans}
        stale_links = FarmCrop.objects.filter(
            farm=farm,
            deleted_at__isnull=True,
        ).exclude(crop_id__in=active_crop_ids)
        if stale_links.exists():
            stale_links.update(deleted_at=timezone.now())
            updated = True

        for plan in active_plans:
            if FarmCrop.objects.filter(
                farm=farm,
                crop=plan.crop,
                deleted_at__isnull=True,
            ).exists():
                continue
            FarmCrop.objects.create(farm=farm, crop=plan.crop)
            updated = True

        for plan in active_plans:
            updated = self._ensure_task_for_crop(
                crop=plan.crop,
                name="خدمة معمرة E2E" if getattr(plan.crop, "is_perennial", False) else "عملية موسمية E2E",
                stage="الرعاية",
                archetype=(
                    TaskModel.Archetype.PERENNIAL_SERVICE
                    if getattr(plan.crop, "is_perennial", False)
                    else TaskModel.Archetype.LABOR_INTENSIVE
                ),
                is_perennial=bool(getattr(plan.crop, "is_perennial", False)),
            ) or updated

        has_perennial_task = Task.objects.filter(
            crop=perennial_plan.crop,
            deleted_at__isnull=True,
        ).exists()
        has_seasonal_task = Task.objects.filter(
            crop=seasonal_plan.crop,
            deleted_at__isnull=True,
        ).exists()
        if not has_perennial_task or not has_seasonal_task:
            raise CommandError("proof_farm_daily_log_context_missing=task_contract_seed")

        return updated

    def handle(self, *args, **options):
        username = os.getenv("E2E_USER") or "e2e_proof_user"
        password = (
            os.getenv("E2E_PASS") or os.getenv("AGRIASSET_E2E_USER_PASSWORD") or "E2EProof#2026"
        )
        proof_farm, smart_card_updated = self._ensure_proof_farm_ready()

        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(
            username=username,
            defaults={"is_active": True, "is_staff": True, "is_superuser": True},
        )
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save(update_fields=["is_active", "is_staff", "is_superuser", "password"])

        FarmMembership.objects.filter(user=user).exclude(farm=proof_farm).delete()
        FarmMembership.objects.update_or_create(
            user=user,
            farm=proof_farm,
            defaults={"role": "مدير النظام"},
        )

        self.stdout.write(self.style.SUCCESS(f"prepared_e2e_user={username}"))
        self.stdout.write(
            self.style.SUCCESS(
                "prepared_proof_farm="
                f"{proof_farm.slug} smart_card_visibility="
                f"{'enabled' if smart_card_updated else 'already_enabled'}"
            )
        )
        self.stdout.write(self.style.SUCCESS("prepared_membership_scope=proof_farm_only"))
