from .settings import *  # noqa
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = True
APP_REQUIRE_VERSION_HEADER = False
DB_ENGINE = 'django.db.backends.sqlite3'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv('DB_NAME', str(BASE_DIR / 'test_sqlite.sqlite3')),
        'TEST': {
            'NAME': os.getenv('DB_TEST_NAME', str(BASE_DIR / 'test_sqlite_test.sqlite3')),
        },
    }
}

class DisableMigrations(dict):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
CELERY_TASK_ALWAYS_EAGER = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
# Keep middleware enabled to preserve governance behavior during tests.

from django.db.models.signals import class_prepared
from django.contrib.postgres.constraints import ExclusionConstraint

from django.contrib.postgres.fields import DateRangeField

# ---------------------------------------------------------------------
# SQLite test compatibility:
# DateRangeField is PostgreSQL-native. For SQLite-based tests we map it
# to TEXT storage to allow schema creation. Business logic using daterange
# is verified via PostgreSQL migrations/runtime probes in real environments.
# ---------------------------------------------------------------------
_original_daterange_db_type = DateRangeField.db_type
def _sqlite_compatible_db_type(self, connection):  # noqa: ANN001
    if getattr(connection, "vendor", "") == "sqlite":
        return "text"
    return _original_daterange_db_type(self, connection)
DateRangeField.db_type = _sqlite_compatible_db_type  # type: ignore



def _strip_postgres_only_constraints(sender, **kwargs):
    meta = getattr(sender, '_meta', None)
    if not meta:
        return
    meta.constraints = [c for c in meta.constraints if not isinstance(c, ExclusionConstraint)]

class_prepared.connect(_strip_postgres_only_constraints)
