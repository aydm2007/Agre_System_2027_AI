from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed the official Al Husseiniya UAT farm."

    def add_arguments(self, parser):
        parser.add_argument("--clean", action="store_true", default=False, help="Reset existing UAT data first.")

    def handle(self, *args, **options):
        from smart_agri.core.uat.al_husseiniya import seed_al_husseiniya_uat

        ctx = seed_al_husseiniya_uat(clean=options["clean"], verbose=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {ctx.farm.name} ({ctx.farm.slug}) in mode={ctx.settings.mode} tier={ctx.governance.tier}"
            )
        )
