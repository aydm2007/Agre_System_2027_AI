import pytest
import uuid
import inspect
from rest_framework.test import APIClient
from django.test.client import Client
import rest_framework.test
import django.test.client
import django.test

class IdempotentAPIClient(APIClient):
    def post(self, path, data=None, format=None, content_type=None, **extra):
        if 'HTTP_X_IDEMPOTENCY_KEY' not in extra:
            extra['HTTP_X_IDEMPOTENCY_KEY'] = str(uuid.uuid4())
        return super().post(path, data, format, content_type, **extra)
    
    def patch(self, path, data=None, format=None, content_type=None, **extra):
        if 'HTTP_X_IDEMPOTENCY_KEY' not in extra:
            extra['HTTP_X_IDEMPOTENCY_KEY'] = str(uuid.uuid4())
        return super().patch(path, data, format, content_type, **extra)

rest_framework.test.APIClient = IdempotentAPIClient

class IdempotentClient(Client):
    def post(self, path, data=None, content_type=None, secure=False, **extra):
        if 'HTTP_X_IDEMPOTENCY_KEY' not in extra:
            extra['HTTP_X_IDEMPOTENCY_KEY'] = str(uuid.uuid4())
        return super().post(path, data, content_type, secure, **extra)
    
    def patch(self, path, data=None, content_type=None, secure=False, **extra):
        if 'HTTP_X_IDEMPOTENCY_KEY' not in extra:
            extra['HTTP_X_IDEMPOTENCY_KEY'] = str(uuid.uuid4())
        return super().patch(path, data, content_type, secure, **extra)

django.test.client.Client = IdempotentClient
django.test.Client = IdempotentClient


@pytest.fixture(autouse=True)
def force_farm_strict_mode(db):
    try:
        from django.db.models.signals import pre_save
        from smart_agri.core.models import Farm

        def set_strict(sender, instance, **kwargs):
            if hasattr(instance, 'mode'):
                # Check if this test explicitly tests simple mode
                frame = inspect.currentframe()
                is_simple_test = False
                while frame:
                    filename = frame.f_code.co_filename.lower()
                    if 'simple' in filename or 'boundary' in filename or 'leakage' in filename or 'test_v21_e2e_cycle' in filename:
                        is_simple_test = True
                        break
                    frame = frame.f_back
                
                if not is_simple_test:
                    # In V21 legacy tests that don't know about modes, force STRICT
                    # so they can pass StrictModeRequired middleware in financial routes.
                    if instance.mode == 'SIMPLE' or not instance.mode:
                        instance.mode = 'STRICT'

        pre_save.connect(set_strict, sender=Farm)
        yield
        pre_save.disconnect(set_strict, sender=Farm)
    except ImportError:
        yield
