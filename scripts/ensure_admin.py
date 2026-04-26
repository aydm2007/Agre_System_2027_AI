import os
import secrets
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()


def create_admin():
    username = os.getenv('AGRIASSET_ADMIN_USERNAME', 'admin')
    email = os.getenv('AGRIASSET_ADMIN_EMAIL', 'admin@example.com')
    password = os.getenv('AGRIASSET_ADMIN_PASSWORD') or secrets.token_urlsafe(12)
    user, created = User.objects.get_or_create(username=username, defaults={'email': email, 'is_staff': True, 'is_superuser': True})
    user.email = email
    user.is_staff = True
    user.is_superuser = True
    user.set_password(password)
    user.save()
    print(f'PASSWORD={password}')


if __name__ == '__main__':
    create_admin()
