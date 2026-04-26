
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smart_agri.settings")
django.setup()

User = get_user_model()
USERNAME = "Ibrahim"
PASSWORD = "12345"

def fix_user():
    print(f"🔧 Checking User: {USERNAME}...")
    
    try:
        user = User.objects.get(username=USERNAME)
        print("✅ User found.")
    except User.DoesNotExist:
        print("⚠️ User NOT found. Creating...")
        user = User(username=USERNAME)
        # Set essential fields if needed
        if hasattr(user, 'email'):
            user.email = "ibrahim@agri-guardian.local"
        if hasattr(user, 'is_staff'):
            user.is_staff = True
        if hasattr(user, 'is_superuser'):
            user.is_superuser = True
    
    # Ensure active
    if not user.is_active:
        print("⚠️ User was inactive. Reactivating...")
        user.is_active = True
    
    # Reset Password
    print(f"🔑 Resetting password to: '{PASSWORD}'")
    user.set_password(PASSWORD)
    user.save()
    
    print(f"✅ User '{USERNAME}' is now Active and Ready.")
    
    # Verify
    from django.contrib.auth import authenticate
    u = authenticate(username=USERNAME, password=PASSWORD)
    if u:
        print("🎉 Authentication Verification: SUCCESS")
    else:
        print("❌ Authentication Verification: FAILED (Check Auth Backend?)")

if __name__ == "__main__":
    fix_user()
