import hashlib
import json
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework import status

from smart_agri.core.models import IdempotencyRecord
from smart_agri.core.api.utils import _sync_pk_sequence

logger = logging.getLogger(__name__)

IDEMPOTENCY_LOCK_TIMEOUT = getattr(settings, 'IDEMPOTENCY_LOCK_TIMEOUT', 300)  # 5 minutes default

class IdempotencyLocked(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "العملية قيد التنفيذ حالياً. يرجى الانتظار."
    default_code = "idempotency_locked"

class IdempotencyMismatch(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "تم استخدام نفس مفتاح عدم التكرار مع بيانات مختلفة."
    default_code = "idempotency_mismatch"

class IdempotencyService:
    """
    Service to handle Idempotency V2 (Acquire-Then-Execute) pattern.
    """

    @staticmethod
    def get_lock_expiry():
        return timezone.now() + timedelta(seconds=IDEMPOTENCY_LOCK_TIMEOUT)

    @staticmethod
    def calculate_hash(method, path, body, params):
        """
        Create a SHA256 hash of the request signature to detect reuse with different payload.
        """
        payload = {
            'method': str(method).upper(),
            'path': str(path),
            'body': body or {},
            'params': params or {}
        }
        # Sort keys to ensure deterministic hash for JSON
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    @classmethod
    def acquire_lock(cls, key, user, method, path, body=None, params=None, farm_id=None):
        """
        Attempts to acquire a lock for the given idempotency key.
        Returns:
            (record, is_replay, response_tuple)
            
            - record: The IdempotencyRecord instance (if acquired or found).
            - is_replay: Boolean, True if we should return cached response.
            - response_tuple: (status, body) if is_replay is True, else None.
            
        Raises:
            IdempotencyLocked: If key is currently locked (IN_PROGRESS).
            IdempotencyMismatch: If key exists but hash differs.
        """
        request_hash = cls.calculate_hash(method, path, body, params)
        
        # 1. Try to create a new IN_PROGRESS record
        try:
            with transaction.atomic():
                record = IdempotencyRecord.objects.create(
                    key=key,
                    user=user,
                    farm_id=farm_id,
                    method=method,
                    path=path,
                    request_hash=request_hash,
                    status=IdempotencyRecord.STATUS_IN_PROGRESS,
                    expiry_at=cls.get_lock_expiry(),
                    model='',
                    object_id=''
                )
                # Acquired successfully
                return record, False, None
        except IntegrityError:
            # Record exists, fall through to handle existing record
            pass

        # 2. Handle existing record
        try:
            record = IdempotencyRecord.objects.get(
                key=key, 
                user=user, 
                method=method, 
                path=path
            )
        except IdempotencyRecord.DoesNotExist:
            # Race condition edge case: Created but deleted? Or validation error on retrieval.
            # Should not happen typically if unique constraint triggered IntegrityError.
            # But maybe another thread/process managed to insert it.
            # Let's retry creation or fail.
            raise IdempotencyLocked("تضارب في البيانات. يرجى المحاولة مرة أخرى.")

        # 3. Validation: Check Hash Mismatch
        if record.request_hash and record.request_hash != request_hash:
             # Allow hash update if the previous attempt explicitly failed, so users can fix validation errors.
             if record.status == IdempotencyRecord.STATUS_FAILED:
                 logger.info(f"Idempotency retry with modified data for failed key {key}. Updating hash.")
                 record.request_hash = request_hash
                 record.save(update_fields=['request_hash'])
             else:
                 raise IdempotencyMismatch(f"تم استخدام المفتاح '{key}' مسبقاً مع بيانات مختلفة.")

        # 4. Legacy compatibility:
        # Some older callers persisted response fields without flipping status to SUCCEEDED.
        # If we already have a concrete cached response, replay deterministically.
        if record.response_status and record.response_body is not None:
            return record, True, (record.response_status, record.response_body)

        # 5. Check Status
        if record.status == IdempotencyRecord.STATUS_SUCCEEDED:
            if record.response_status and record.response_body is not None:
                return record, True, (record.response_status, record.response_body)
            # If succeeded but no response stored (legacy?), likely safe to ignore or return 200 OK empty
            return record, True, (200, record.response_body or {})

        if record.status == IdempotencyRecord.STATUS_FAILED:
            # Previous attempt failed, we treat this as a "Retry" > Acquire Lock again
            # We must reset the record to IN_PROGRESS
            return cls._reset_to_progress(record)

        if record.status == IdempotencyRecord.STATUS_IN_PROGRESS:
            now = timezone.now()
            if record.expiry_at and now > record.expiry_at:
                # Lock expired (Zombie transaction), force acquire
                logger.warning(f"Idempotency lock expired for key {key}. taking over.")
                return cls._reset_to_progress(record)
            
            # Still locked
            raise IdempotencyLocked(f"الطلب قيد المعالجة (جاري التنفيذ). الرجاء الانتظار.")
            
        # Default fallback
        return cls._reset_to_progress(record)

    @classmethod
    def _reset_to_progress(cls, record):
        from django.db import transaction
        with transaction.atomic():
            # Re-fetch with lock to prevent race condition under high concurrency / weak networks
            record = IdempotencyRecord.objects.select_for_update().get(pk=record.pk)
            record.status = IdempotencyRecord.STATUS_IN_PROGRESS
            record.expiry_at = cls.get_lock_expiry()
            record.save(update_fields=['status', 'expiry_at', 'updated_at'])
        return record, False, None

    @classmethod
    def commit_success(cls, record, response_status, response_body, object_id='', model_name=''):
        """
        Finalize the record as SUCCEEDED with response.
        """
        import json
        from django.core.serializers.json import DjangoJSONEncoder
        try:
            safe_body = json.loads(json.dumps(response_body, cls=DjangoJSONEncoder))
        except (TypeError, ValueError):
            safe_body = response_body

        record.status = IdempotencyRecord.STATUS_SUCCEEDED
        record.response_status = response_status
        record.response_body = safe_body
        record.object_id = str(object_id)
        if model_name:
            record.model = model_name
        record.save(update_fields=['status', 'response_status', 'response_body', 'object_id', 'model', 'updated_at'])

    @classmethod
    def commit_failure(cls, record, note=""):
        """
        Mark record as FAILED to allow retries.
        """
        record.status = IdempotencyRecord.STATUS_FAILED
        record.save(update_fields=['status', 'updated_at'])
