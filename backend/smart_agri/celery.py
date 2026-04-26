
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')

app = Celery('smart_agri')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# [AGRI-GUARDIAN] Celery Beat Schedule — Monthly Agronomic Tasks
app.conf.beat_schedule = {
    # Axis 11: Biological Asset Amortization (PRODUCTIVE cohorts)
    'bio-amortization-monthly': {
        'task': 'smart_agri.core.tasks.agronomic_tasks.run_bio_amortization_all_farms',
        'schedule': crontab(day_of_month='1', hour='2', minute='0'),
        'options': {'queue': 'agronomic'},
    },
    # Axis 9: Fixed Asset Depreciation (IAS 16)
    'asset-depreciation-monthly': {
        'task': 'smart_agri.core.tasks.agronomic_tasks.run_asset_depreciation_all_farms',
        'schedule': crontab(day_of_month='1', hour='3', minute='0'),
        'options': {'queue': 'agronomic'},
    },
    'integration-outbox-dispatch-every-minute': {
        'task': 'smart_agri.core.tasks.integration_tasks.dispatch_integration_outbox_async',
        'schedule': crontab(minute='*/1'),
        'kwargs': {'batch_size': 200},
        'options': {'queue': 'integration'},
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

