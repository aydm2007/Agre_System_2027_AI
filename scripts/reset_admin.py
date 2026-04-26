import os
import secrets
import sys
import django

sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()


def reset_admin():
    password = os.getenv('AGRIASSET_ADMIN_PASSWORD') or secrets.token_urlsafe(12)
    user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com', 'is_active': True, 'is_staff': True, 'is_superuser': True})
    user.set_password(password)
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f'PASSWORD={password}')


if __name__ == '__main__':
    reset_admin()
