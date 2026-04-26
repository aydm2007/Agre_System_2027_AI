"""
[AGRI-GUARDIAN] Agronomic Cycle Celery Beat Tasks.

Scheduled periodic tasks for the agronomic cycle:
1. Monthly Biological Asset Amortization (Axis 11)
2. Monthly Asset Depreciation (IAS 16)

These tasks are intended to be scheduled via Celery Beat (crontab).
Configuration should be added to the Django settings or celery.py:

    CELERY_BEAT_SCHEDULE = {
        'bio-amortization-monthly': {
            'task': 'smart_agri.core.tasks.agronomic_tasks.run_bio_amortization_all_farms',
            'schedule': crontab(day_of_month='1', hour='2', minute='0'),
        },
        'asset-depreciation-monthly': {
            'task': 'smart_agri.core.tasks.agronomic_tasks.run_asset_depreciation_all_farms',
            'schedule': crontab(day_of_month='1', hour='3', minute='0'),
        },
    }
"""

import logging
from datetime import date

from celery import shared_task
from django.core.exceptions import ValidationError, ObjectDoesNotExist

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_bio_amortization_for_farm(self, farm_id, year=None, month=None, user_id=None):
    """
    [AGRI-GUARDIAN §Axis-11] Monthly Biological Asset Amortization for a single farm.
    Posts DR 7000-DEP-EXP / CR 1600-BIO-ASSET for all PRODUCTIVE cohorts.

    Should be called on the 1st of every month via Celery Beat.
    """
    from smart_agri.core.services.bio_amortization_service import BiologicalAmortizationService
    from django.contrib.auth import get_user_model

    User = get_user_model()
    today = date.today()
    year = year or today.year
    month = month or today.month

    user = None
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.warning("[Celery] User not found for bio amortization task: user_id=%s", user_id)

    try:
        result = BiologicalAmortizationService.run_monthly_amortization(
            farm_id=farm_id,
            year=year,
            month=month,
            user=user,
        )
        logger.info(
            "[Celery] Bio amortization completed: farm=%s, period=%s-%02d, status=%s",
            farm_id, year, month, result.get('status'),
        )
        return result
    except ValidationError as e:
        logger.error("[Celery] Bio amortization validation error: farm=%s, %s", farm_id, e)
        raise
    except (RuntimeError, OSError, ValueError, ObjectDoesNotExist) as e:
        logger.error("[Celery] Bio amortization failed: farm=%s, %s", farm_id, e)
        raise self.retry(exc=e)


@shared_task(bind=True)
def run_bio_amortization_all_farms(self, year=None, month=None):
    """
    [AGRI-GUARDIAN §Axis-11] Dispatch monthly bio amortization for ALL active farms.
    Used as the Celery Beat entry point.
    """
    from smart_agri.core.models.farm import Farm

    today = date.today()
    year = year or today.year
    month = month or today.month

    active_farms = Farm.objects.filter(
        deleted_at__isnull=True,
        is_active=True,
    ).values_list('id', flat=True)

    dispatched = 0
    for farm_id in active_farms:
        run_bio_amortization_for_farm.delay(farm_id, year, month)
        dispatched += 1

    logger.info(
        "[Celery] Bio amortization dispatched for %d farms, period=%s-%02d",
        dispatched, year, month,
    )
    return {"dispatched": dispatched, "period": f"{year}-{month:02d}"}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_asset_depreciation_for_farm(self, farm_id=None, user_id=None):
    """
    [AGRI-GUARDIAN §Axis-9] Monthly Asset Depreciation (IAS 16).
    Runs straight-line depreciation for all active assets.
    """
    from smart_agri.core.services.asset_service import AssetService
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = None
    if user_id:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.warning("[Celery] User not found for asset depreciation task: user_id=%s", user_id)

    try:
        AssetService.run_monthly_depreciation(user=user)
        logger.info("[Celery] Asset depreciation completed.")
        return {"status": "completed"}
    except (RuntimeError, OSError, ValueError, ObjectDoesNotExist) as e:
        logger.error("[Celery] Asset depreciation failed: %s", e)
        raise self.retry(exc=e)


@shared_task(bind=True)
def run_asset_depreciation_all_farms(self):
    """
    [AGRI-GUARDIAN §Axis-9] Dispatch monthly asset depreciation.
    Used as the Celery Beat entry point.
    """
    run_asset_depreciation_for_farm.delay()
    logger.info("[Celery] Asset depreciation dispatched.")
    return {"status": "dispatched"}
