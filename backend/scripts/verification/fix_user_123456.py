
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

User = get_user_model()
USERNAME = "Ibrahim"
PASSWORD = "123456"  # Changed as per user request

def fix_user():
    print(f"🔧 Updating User: {USERNAME}...")
    try:
        user = User.objects.get(username=USERNAME)
        user.set_password(PASSWORD)
        user.save()
        print(f"✅ Password updated to '{PASSWORD}'")
    except User.DoesNotExist:
        print("❌ User not found!")

if __name__ == "__main__":
    fix_user()
