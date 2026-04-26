import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.contrib.auth import get_user_model
from smart_agri.core.models import Farm, FarmMembership

User = get_user_model()
admin_users = User.objects.filter(is_superuser=True)
farms = Farm.objects.all()

for admin in admin_users:
    for farm in farms:
        FarmMembership.objects.get_or_create(
            user=admin,
            farm=farm,
            defaults={"role": "Admin"}
        )
        print(f"Ensured FarmMembership for {admin.username} on {farm.name}")

print("Membership fix complete.")
