"""
Production Settings - AGRI-MAESTRO Phase 3.2 Security Hardening
Resolves security.W008, W012, W016 warnings
All environment variables are REQUIRED for production deployment

MOVED FROM: smart_agri/settings/production.py
TO: smart_agri/production_settings.py
REASON: Avoid conflict with settings.py (Python imports directory over file)
"""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Import all base settings
from smart_agri.settings import *  # noqa: F401, F403
from smart_agri.env_utils import get_first_env, parse_csv_env

def get_env_variable(var_name):
    try:
        return os.environ[var_name]
    except KeyError:
        # [Agri-Guardian] Fail-Safe: Crash immediately if security keys are missing.
        error_msg = f"CRITICAL SECURITY ERROR: Set the {var_name} environment variable."
        raise ImproperlyConfigured(error_msg)

# Override DEBUG
DEBUG = False

# CRITICAL: Secret Key MUST be set via environment
SECRET_KEY = get_env_variable('DJANGO_SECRET_KEY')

# CRITICAL: Allowed Hosts MUST be explicitly set
# Format: "domain1.com,domain2.com,ip1,ip2"
ALLOWED_HOSTS = parse_csv_env('DJANGO_ALLOWED_HOSTS', 'ALLOWED_HOSTS')
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured('CRITICAL SECURITY ERROR: Set DJANGO_ALLOWED_HOSTS or ALLOWED_HOSTS.')

# ============================================================================
# SSL/HTTPS Settings (Fixes security.W008)
# ============================================================================
SECURE_SSL_REDIRECT = True  # ✅ Force HTTPS for all requests
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ============================================================================
# Cookie Security (Fixes security.W012, W016)
# ============================================================================
SESSION_COOKIE_SECURE = True  # ✅ HTTPS-only session cookies
CSRF_COOKIE_SECURE = True  # ✅ HTTPS-only CSRF cookies
CSRF_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
CSRF_COOKIE_SAMESITE = 'Lax'

# ============================================================================
# HSTS (HTTP Strict Transport Security)
# ============================================================================
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ============================================================================
# Content Security
# ============================================================================
SECURE_CONTENT_TYPE_NOSNIFF = True  # Prevent MIME sniffing
SECURE_BROWSER_XSS_FILTER = True  # XSS protection
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking

# ============================================================================
# Database - Production with Connection Pooling
# ============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'agriasset_prod'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ['DB_PASSWORD'],  # Required
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling (10 minutes)
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30 seconds
        },
    }
}

# ============================================================================
# Logging - Production Level
# ============================================================================
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'production.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'WARNING',
    },
    'loggers': {
        'smart_agri': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ============================================================================
# CORS - Production (Strict)
# ============================================================================
CORS_ALLOW_ALL_ORIGINS = False  # Never allow all in production
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    ''
).split(',')

# ============================================================================
# CSRF - Production
# ============================================================================
CSRF_TRUSTED_ORIGINS = [
    origin.replace('http://', 'https://') if origin.startswith('http://') else origin
    for origin in CORS_ALLOWED_ORIGINS
]

# ============================================================================
# Static Files - WhiteNoise Configuration
# ============================================================================
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================================
# AGRI-MAESTRO Settings
# ============================================================================
COSTING_STRICT_MODE = True  # Always strict in production

# ============================================================================
# Deployment Verification
# ============================================================================
# [AG-CLEANUP] print("🛡️ Production Settings Loaded")
# [AG-CLEANUP] print(f"   DEBUG: {DEBUG}")
# [AG-CLEANUP] print(f"   ALLOWED_HOSTS: {ALLOWED_HOSTS}")
# [AG-CLEANUP] print(f"   SSL_REDIRECT: {SECURE_SSL_REDIRECT}")
# [AG-CLEANUP] print(f"   COSTING_STRICT_MODE: {COSTING_STRICT_MODE}")
