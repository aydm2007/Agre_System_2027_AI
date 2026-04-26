from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Crop, CropPlan, Farm, Location, Season, Task
from smart_agri.core.models.crop import FarmCrop
from smart_agri.core.models.settings import FarmSettings


class PrepareE2EAuthCommandTests(TestCase):
    def test_prepare_e2e_auth_enables_sardood_smart_card_visibility(self):
        farm = Farm.objects.create(
            name="مزرعة سردود",
            slug="sardood-farm",
            region="تهامة",
        )
        FarmSettings.objects.create(
            farm=farm,
            mode=FarmSettings.MODE_SIMPLE,
            show_daily_log_smart_card=False,
        )

        stdout = StringIO()
        call_command("prepare_e2e_auth_v21", stdout=stdout)

        settings = FarmSettings.objects.get(farm=farm)
        self.assertTrue(settings.show_daily_log_smart_card)

        user = get_user_model().objects.get(username="e2e_proof_user")
        membership = FarmMembership.objects.get(user=user, farm=farm)
        self.assertEqual(membership.role, "Admin")

        output = stdout.getvalue()
        self.assertIn("prepared_e2e_user=e2e_proof_user", output)
        self.assertIn("prepared_proof_farm=sardood-farm", output)

    def test_prepare_e2e_auth_normalizes_legacy_sardood_slug(self):
        farm = Farm.objects.create(
            name="\u0645\u0632\u0631\u0639\u0629 \u0633\u0631\u062f\u0648\u062f",
            slug="legacy-sardood",
            region="\u062a\u0647\u0627\u0645\u0629",
        )
        FarmSettings.objects.create(
            farm=farm,
            mode=FarmSettings.MODE_SIMPLE,
            show_daily_log_smart_card=False,
        )

        stdout = StringIO()
        call_command("prepare_e2e_auth_v21", stdout=stdout)

        farm.refresh_from_db()
        settings = FarmSettings.objects.get(farm=farm)

        self.assertEqual(farm.slug, "sardood-farm")
        self.assertTrue(settings.show_daily_log_smart_card)
        self.assertIn("prepared_proof_farm=sardood-farm", stdout.getvalue())

    def test_prepare_e2e_auth_rejects_conflicting_sardood_records(self):
        Farm.objects.create(
            name="Legacy Conflict",
            slug="sardood-farm",
            region="\u062a\u0647\u0627\u0645\u0629",
        )
        Farm.objects.create(
            name="\u0645\u0632\u0631\u0639\u0629 \u0633\u0631\u062f\u0648\u062f",
            slug="legacy-sardood",
            region="\u062a\u0647\u0627\u0645\u0629",
        )

        with self.assertRaisesMessage(CommandError, "proof_farm_conflict"):
            call_command("prepare_e2e_auth_v21")

    def test_prepare_e2e_auth_blocks_when_daily_log_context_cannot_be_seeded(self):
        farm = Farm.objects.create(
            name="\u0645\u0632\u0631\u0639\u0629 \u0633\u0631\u062f\u0648\u062f",
            slug="sardood-farm",
            region="\u062a\u0647\u0627\u0645\u0629",
        )
        FarmSettings.objects.create(
            farm=farm,
            mode=FarmSettings.MODE_SIMPLE,
            show_daily_log_smart_card=False,
        )

        with patch(
            "smart_agri.core.management.commands.prepare_e2e_auth_v21.call_command"
        ) as mocked_call_command:
            mocked_call_command.return_value = None
            with self.assertRaisesMessage(
                CommandError,
                "proof_farm_daily_log_context_missing=seasonal_or_perennial_plan",
            ):
                call_command("prepare_e2e_auth_v21")

    def test_prepare_e2e_auth_seeds_daily_log_context_tasks_for_active_plans(self):
        today = timezone.localdate()
        farm = Farm.objects.create(
            name="\u0645\u0632\u0631\u0639\u0629 \u0633\u0631\u062f\u0648\u062f",
            slug="sardood-farm",
            region="\u062a\u0647\u0627\u0645\u0629",
        )
        FarmSettings.objects.create(
            farm=farm,
            mode=FarmSettings.MODE_SIMPLE,
            show_daily_log_smart_card=False,
        )
        season = Season.objects.create(
            name=f"Proof {today.year}",
            start_date=today.replace(month=1, day=1),
            end_date=today.replace(month=12, day=31),
            is_active=True,
        )
        location = Location.objects.create(farm=farm, name="\u0627\u0644\u062d\u0642\u0644 \u0627\u0644\u0631\u0626\u064a\u0633\u064a", code="SRD-E2E")
        seasonal_crop = Crop.objects.create(name="Seasonal Proof Crop", mode="Open", is_perennial=False)
        perennial_crop = Crop.objects.create(name="Perennial Proof Crop", mode="Open", is_perennial=True)
        stale_crop = Crop.objects.create(name="Stale Proof Crop", mode="Open", is_perennial=False)
        stale_link = FarmCrop.objects.create(farm=farm, crop=stale_crop)
        CropPlan.objects.create(
            farm=farm,
            season=season,
            crop=seasonal_crop,
            name="Seasonal proof plan",
            start_date=today,
            end_date=today,
            status="active",
        )
        CropPlan.objects.create(
            farm=farm,
            season=season,
            crop=perennial_crop,
            name="Perennial proof plan",
            start_date=today,
            end_date=today,
            status="active",
        )

        stdout = StringIO()
        call_command("prepare_e2e_auth_v21", stdout=stdout)

        self.assertTrue(Task.objects.filter(crop=seasonal_crop, deleted_at__isnull=True).exists())
        perennial_task = Task.objects.filter(crop=perennial_crop, deleted_at__isnull=True).first()
        self.assertIsNotNone(perennial_task)
        self.assertTrue(perennial_task.requires_tree_count)
        self.assertTrue(perennial_task.is_perennial_procedure)
        self.assertTrue(FarmCrop.objects.filter(farm=farm, crop=seasonal_crop, deleted_at__isnull=True).exists())
        self.assertTrue(FarmCrop.objects.filter(farm=farm, crop=perennial_crop, deleted_at__isnull=True).exists())
        stale_link.refresh_from_db()
        self.assertIsNotNone(stale_link.deleted_at)
        self.assertTrue(Location.objects.filter(pk=location.pk, farm=farm).exists())
