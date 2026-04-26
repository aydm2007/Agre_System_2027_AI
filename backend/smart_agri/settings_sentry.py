
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations import DidNotEnable
try:
    from sentry_sdk.integrations.celery import CeleryIntegration
except (DidNotEnable, ImportError, ModuleNotFoundError):
    CeleryIntegration = None  # type: ignore

import os
import logging

logger = logging.getLogger(__name__)

def init_sentry():
    """
    Initialize Sentry with production-grade settings.
    Protocol: OBSERVABILITY-V1
    """
    SENTRY_DSN = os.environ.get("SENTRY_DSN")
    SERVER_ENV = os.environ.get("SERVER_ENV", "development")

    if not SENTRY_DSN:
        if SERVER_ENV == "production":
            logger.warning("⚠️ SENTRY_DSN is missing in PRODUCTION! Observability is compromised.")
        return

    integrations_list = [DjangoIntegration(), RedisIntegration()]
    if CeleryIntegration is not None:
        integrations_list.append(CeleryIntegration())

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=integrations_list,
        
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # Adjust in high-load production.
        traces_sample_rate=0.1 if SERVER_ENV == "production" else 1.0,

        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
        
        environment=SERVER_ENV,
        release=os.environ.get("GIT_SHA", "unknown")
    )
    
    logger.info(f"✅ Sentry initialized in {SERVER_ENV} mode.")
