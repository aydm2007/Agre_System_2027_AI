import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from django.apps import apps
from django.contrib.contenttypes.models import ContentType

print("=== Model Verbose Names ===")
for app_config in apps.get_app_configs():
    if not app_config.name.startswith('smart_agri'):
        continue
    for model in app_config.get_models():
        print(f"{model.__name__} (Table: {model._meta.db_table})")
        print(f"  VERBOSE NAME: {model._meta.verbose_name}")
        print(f"  VERBOSE NAME PLURAL: {model._meta.verbose_name_plural}")
        # print specific permissions
        if model._meta.permissions:
            print(f"  CUSTOM PERMISSIONS: {model._meta.permissions}")
