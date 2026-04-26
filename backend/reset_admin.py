from django.contrib.auth import get_user_model
User = get_user_model()
try:
    admin, created = User.objects.get_or_create(username='admin')
    admin.set_password('admin123')
    admin.save()
    print("✅ Admin password reset to admin123")
except Exception as e:
    print(f"❌ Error setting admin password: {e}")
