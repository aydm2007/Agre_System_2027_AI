import sys
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')

import django
django.setup()

from django.conf import settings
print(settings.INSTALLED_APPS)
