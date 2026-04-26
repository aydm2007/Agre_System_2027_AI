
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Farm
class Command(BaseCommand):
    help = "Assign a user to a farm with a role. Example: --username admin --farm_slug sardood --role Manager"
    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--farm_slug", required=True)
        parser.add_argument("--role", default="Viewer")
    def handle(self, *args, **opts):
        try:
            user = User.objects.get(username=opts["username"])
            farm = Farm.objects.get(slug=opts["farm_slug"])
            fm, created = FarmMembership.objects.get_or_create(user=user, farm=farm, defaults={"role": opts["role"]})
            if not created: fm.role = opts["role"]; fm.save(update_fields=["role"])
            self.stdout.write(self.style.SUCCESS(f"Assigned {user} -> {farm.slug} ({fm.role})"))
        except User.DoesNotExist:
            raise CommandError("User not found")
        except Farm.DoesNotExist:
            raise CommandError("Farm not found")
