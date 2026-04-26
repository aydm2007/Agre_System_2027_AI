from django.contrib.auth import get_user_model
User = get_user_model()
try:
    user, created = User.objects.get_or_create(username='playwright')
    user.set_password('playwright123')
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.save()
    print("✅ Playwright user created: playwright / playwright123")
except Exception as e:
    print(f"❌ Error setting user: {e}")
