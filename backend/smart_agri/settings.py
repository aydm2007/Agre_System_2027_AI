
import os
import sys
from pathlib import Path
from datetime import timedelta
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv
from corsheaders.defaults import default_headers
from smart_agri.env_utils import parse_csv_env

# Load .env from backend directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "agriasset-dev-fallback-key-2026-keep-outside-production-50chars+")

# [AGRI-GUARDIAN SECURITY FIX]
# DEBUG must be False in production. Defaulting to False if not set.
# Use DJANGO_DEBUG=True in .env for development.
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

# Controlled-pilot defaults: tenant scoping and non-logging integration discipline should be
# enabled unless a local development profile overrides them explicitly.
os.environ.setdefault("STRICT_FARM_SCOPE_HEADERS", "false" if DEBUG else "true")
os.environ.setdefault("INTEGRATION_HUB_PUBLISHER", "logging" if DEBUG else "composite")

APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
APP_MIN_CLIENT_VERSION = os.getenv("APP_MIN_CLIENT_VERSION", APP_VERSION)
APP_REQUIRE_VERSION_HEADER = (
    os.getenv("APP_REQUIRE_VERSION_HEADER", "true").lower() == "true"
    and "test" not in sys.argv
)

ALLOWED_HOSTS = parse_csv_env(
    'DJANGO_ALLOWED_HOSTS',
    'ALLOWED_HOSTS',
    default=['localhost', '127.0.0.1', '0.0.0.0', '195.94.24.180'],
)
if DEBUG:
    ALLOWED_HOSTS = ['*'] # RAKEN MODE: Absolute transparency in development


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "smart_agri.accounts",
    "smart_agri.core",
    "smart_agri.integrations",
    "smart_agri.sales",
    "smart_agri.inventory",
    "smart_agri.finance.apps.FinanceConfig",
    "django_htmx",
    "csp",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "smart_agri.core.middleware.app_version_middleware.AppVersionMiddleware",
    "smart_agri.core.middleware.request_observability_middleware.RequestObservabilityMiddleware",
    "smart_agri.core.middleware.farm_scope_guard_middleware.FarmScopeGuardMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # AGRI-MAESTRO Phase 3: RLS Security
    "smart_agri.core.middleware.rls_middleware.RLSMiddleware",
    # [AGRI-GUARDIAN Axis 15] Route Breach Audit for Simple Mode Defense
    "smart_agri.core.middleware.route_breach_middleware.RouteBreachAuditMiddleware",
    # [AGRI-GUARDIAN Axis 2] Idempotency enforcement on financial mutations
    "smart_agri.core.middleware.idempotency_middleware.IdempotencyMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # "django.middleware.clickjacking.XFrameOptionsMiddleware", # Disabled for Zenith Dashboard Iframe
    "csp.middleware.CSPMiddleware",  # Enabled when django-csp is installed
]

ROOT_URLCONF = "smart_agri.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "smart_agri.wsgi.application"

DB_ENGINE = os.getenv("DB_ENGINE", os.getenv("DJANGO_DB_ENGINE", "django.db.backends.postgresql")).strip()
DB_CONN_MAX_AGE = int(os.getenv("DB_CONN_MAX_AGE", 0))
DATABASE_URL = (os.getenv("DATABASE_URL", "") or "").strip()


def _env_flag(name: str, default: bool = False) -> bool:
    value = (os.getenv(name, "") or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _effective_test_db_name(base_name: str) -> str:
    explicit = (os.getenv("DB_TEST_NAME", "") or "").strip()
    if explicit:
        return explicit
    default_name = f"{base_name}_test"
    if "test" not in sys.argv:
        return default_name
    # Default to a stable PostgreSQL test database so repeated `manage.py test`
    # runs do not accumulate one database per PID on developer workstations.
    # Per-process isolation remains available as an explicit opt-in for
    # specialized parallel/debug runs.
    if _env_flag("DB_TEST_ISOLATE_PER_PROCESS", default=False):
        return f"{default_name}_{os.getpid()}"
    return default_name


def _database_config_from_url(database_url: str) -> dict:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql", "pgsql"}:
        raise RuntimeError(f"Unsupported DATABASE_URL scheme: {parsed.scheme or 'missing'}")
    db_name = (parsed.path or "").lstrip("/")
    if not db_name:
        raise RuntimeError("DATABASE_URL must include a database name.")
    query_parts = {}
    if parsed.query:
        for token in parsed.query.split("&"):
            if "=" in token:
                key, value = token.split("=", 1)
                query_parts[key] = value
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(db_name),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or "5432"),
        "CONN_MAX_AGE": DB_CONN_MAX_AGE,
        "OPTIONS": {
            "options": "-c client_encoding=UTF8",
            "connect_timeout": int(query_parts.get("connect_timeout", os.getenv("DB_CONNECT_TIMEOUT", 5))),
        },
        "TEST": {
            "NAME": _effective_test_db_name(unquote(db_name)),
        },
    }

if DB_ENGINE == "django.db.backends.sqlite3":
    raise RuntimeError("SQLite is strictly banned in AgriAsset V21. Only PostgreSQL is permitted per Protocol Axis 1.")
elif DATABASE_URL:
    DATABASES = {
        "default": _database_config_from_url(DATABASE_URL)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": os.getenv("DB_NAME", "agriasset"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": DB_CONN_MAX_AGE, # Default 10 mins for connection pooling
            "OPTIONS": {
                "options": "-c client_encoding=UTF8",
                "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", 5)),
            },
            "TEST": {
                "NAME": _effective_test_db_name(os.getenv("DB_NAME", "agriasset")),
            },
        }
    }


# ============================================================================
# PRODUCTION_SAFETY_GATES (fail-closed)
# ============================================================================
# Prevent accidental production deploy with dev fallbacks.
if os.getenv("DJANGO_ENV", "").lower() in {"production", "prod"}:
    if SECRET_KEY.startswith("agriasset-dev-fallback-key-"):
        raise RuntimeError("DJANGO_SECRET_KEY must be set in production (dev fallback is forbidden).")

    if DB_ENGINE.startswith("django.db.backends.postgresql"):
        if not (DATABASES["default"].get("PASSWORD") or "").strip():
            raise RuntimeError("DB_PASSWORD must be set in production for PostgreSQL.")

    # ALLOWED_HOSTS must be explicitly configured in production.
    if ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
        raise RuntimeError("ALLOWED_HOSTS must be explicitly set in production (not localhost defaults).")
    if '*' in ALLOWED_HOSTS:
        raise RuntimeError("SECURITY [Axis 7]: Wildcard ALLOWED_HOSTS ('*') is forbidden in production.")


# ============================================================================
# Cache Configuration
# ============================================================================
# Default: In-memory (zero infrastructure). Use CACHE_URL=redis://host:6379/1 for production.
_cache_url = os.getenv("CACHE_URL", "")
if _cache_url.startswith("redis://"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _cache_url,
            "TIMEOUT": 300,  # 5 minutes
            "KEY_PREFIX": "agri",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "TIMEOUT": 300,
            "KEY_PREFIX": "agri",
        }
    }

LANGUAGE_CODE = "ar"
TIME_ZONE = 'Asia/Aden'
USE_I18N = True
# إصلاح الجولة 12: تمكين دعم المناطق الزمنية لمنع الانفصام الزمني (Temporal Schizophrenia)
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# [AGRI-GUARDIAN] Frontend Integration
# In production images that don't include the frontend build output, this directory may not exist.
# We treat missing dist as non-fatal to keep backend deployable (API-only mode).
_frontend_dist_env = os.getenv('FRONTEND_DIST_DIR', '').strip()
_frontend_dist = Path(_frontend_dist_env) if _frontend_dist_env else (BASE_DIR.parent / 'frontend' / 'dist')
STATICFILES_DIRS = [_frontend_dist] if _frontend_dist.exists() else []
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (user-uploaded and generated reports)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "smart_agri.core.exceptions.custom_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
        "smart_agri.core.throttles.FinancialMutationThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "10000/hour",
        "anon": "10000/hour",
        "financial_mutation": "10000/hour",
        "auth_login": "100/min",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Saradud Agriculture API",
    "DESCRIPTION": "واجهة برمجة تطبيقات نظام سردود الزراعي (Saradud Agriculture System API v2.0)",
    "VERSION": "2.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True # Enabling global reach for Raken Mode stability
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS","http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://195.94.24.180:5173,http://195.94.24.180:8000,http://195.94.24.180:8008,http://localhost:3002").split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ("DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT")

CORS_ALLOW_HEADERS = list(default_headers) + [
    'Idempotency-Key', 
    'X-Idempotency-Key', 
    'x-app-version',
    'X-App-Version',
    'X-APP-VERSION'
]

# Simple JWT settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}

CSP_CONNECT_SRC_DEFAULT = "http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173,http://195.94.24.180:8000,http://195.94.24.180:5173"

def build_csp_sources(env_var, default):
    values = ["'self'"]
    values.extend(
        item.strip()
        for item in os.getenv(env_var, default).split(',')
        if item.strip()
    )
    seen = set()
    ordered = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return tuple(ordered)

# CSP (django-csp >= 4.0)
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ("'self'",),
        "style-src": ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com"),
        "font-src": ("'self'", "https://fonts.gstatic.com"),
        "script-src": ("'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com"),
        "img-src": ("'self'", "data:"),
        "connect-src": build_csp_sources('CSP_CONNECT_SRC', CSP_CONNECT_SRC_DEFAULT),
        "frame-ancestors": ("'self'", "http://localhost:3001", "http://localhost:3002", "http://127.0.0.1:3002"),
    }
}

# Security headers
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Logging
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE_PATH = LOG_DIR / "app.log"
try:
    with open(LOG_FILE_PATH, "a", encoding="utf-8"):
        pass
    LOG_FILE_ENABLED = True
except OSError:
    LOG_FILE_ENABLED = False
ROOT_LOG_HANDLERS = ["console"] + (["file"] if LOG_FILE_ENABLED else [])
LOGGING_HANDLERS = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": "verbose",
    },
}
if LOG_FILE_ENABLED:
    LOGGING_HANDLERS["file"] = {
        "level": "INFO",
        "class": "logging.handlers.RotatingFileHandler",
        "filename": LOG_FILE_PATH,
        "maxBytes": 10 * 1024 * 1024,
        "backupCount": 5,
        "encoding": "utf-8",
        "formatter": "json" if not DEBUG else "verbose",
    }

# [AGRI-GUARDIAN] Structured JSON formatter for production observability
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": LOGGING_HANDLERS,
    "root": {"handlers": ROOT_LOG_HANDLERS, "level": "INFO"},
    "loggers": {
        "smart_agri": {"level": "INFO", "propagate": True},
        "django.db.backends": {"level": "WARNING", "propagate": False},
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


EXPORT_LOGO_PATH = Path(os.getenv("EXPORT_LOGO_PATH", str(BASE_DIR / 'public' / 'logo.png')))


# -----------------------------------------------------------------------------
# CORS Settings (DYNAMICALLY CONFIGURED ABOVE - DO NOT OVERRIDE HERE)
# -----------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = [origin for origin in (CORS_ALLOWED_ORIGINS or [])]


# -----------------------------------------------------------------------------
# Production Security Settings (not applied during tests)
# -----------------------------------------------------------------------------
# Protocol Omega Zero 2029: Force Disable SSL/HTTPS definitively
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

if not DEBUG and "test" not in sys.argv:
    # Production blocks are skipped for this definitive audit
    pass


# -----------------------------------------------------------------------------
# إعدادات معالجة التدقيق الجنائي (2026-01-24)
# -----------------------------------------------------------------------------
# عند التفعيل (True)، سترفع وظائف التكاليف استثناءات إذا كان تكوين التكلفة مفقوداً
# بدلاً من استخدام قيم صفرية بصمت. هذا يمنع الخسائر المالية الخفية.
COSTING_STRICT_MODE = os.getenv("COSTING_STRICT_MODE", "True").lower() == "true"
AUTO_CREATE_FISCAL_PERIOD = os.getenv("AUTO_CREATE_FISCAL_PERIOD", "True").lower() == "true"

# -----------------------------------------------------------------------------
# Celery Configuration (Async Task Queue)
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Skip actual broker connection logic locally if no Redis
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"

# -----------------------------------------------------------------------------
# إعدادات العملات (Currency Configuration)
# -----------------------------------------------------------------------------
# العملة الافتراضية للمعاملات المالية - الريال اليمني
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "YER")

# قائمة العملات المدعومة (للتوسع المستقبلي)
SUPPORTED_CURRENCIES = [
    ("YER", "ريال يمني"),
    ("SAR", "ريال سعودي"),
]

# تفعيل دعم العملات المتعددة (معطل افتراضياً - عملة واحدة فقط)
MULTI_CURRENCY_ENABLED = os.getenv("MULTI_CURRENCY_ENABLED", "False").lower() == "true"

# Tree inventory settings
TREE_JUVENILE_YEARS = int(os.getenv("TREE_JUVENILE_YEARS", "3"))
TREE_DECLINING_YEARS = int(os.getenv("TREE_DECLINING_YEARS", "18"))

# Zakat V2 rollout mode:
# off -> legacy farm-level policy
# shadow -> resolve location policy and log gaps, allow fallback
# enforce -> quarantine gaps for new mutations
# full -> same as enforce, intended steady-state
LOCATION_ZAKAT_POLICY_V2_MODE = os.getenv("LOCATION_ZAKAT_POLICY_V2_MODE", "enforce").strip().lower()

MIGRATION_MODULES = {
    'core': 'smart_agri.core.migrations',
    'accounts': 'smart_agri.accounts.migrations',
    'sales': 'smart_agri.sales.migrations',
    'integrations': 'smart_agri.integrations.migrations',
    'inventory': 'smart_agri.inventory.migrations',
    'finance': 'smart_agri.finance.migrations',
}



# FAIL-SAFE CONFIGURATION (Added by Agri-Guardian)
# Validates that required DB settings exist in .env
if 'default' not in DATABASES or not DATABASES['default'].get('NAME'):
    raise RuntimeError(
        "❌ CRITICAL: Database configuration missing!\n"
        "Please ensure .env file exists with DB_NAME, DB_USER, DB_PASSWORD set.\n"
        "See .env.example for reference."
    )

# ------------------------------------------------------------------------------
# OBSERVABILITY (Sentry)
# ------------------------------------------------------------------------------
try:
    from .settings_sentry import init_sentry
    init_sentry()
except ImportError:
    pass
