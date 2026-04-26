"""
Base ViewSets and Mixins
"""
import logging
from rest_framework import viewsets, permissions, status, exceptions
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from django.db import transaction, OperationalError
from django.db.utils import IntegrityError
from django.core.exceptions import FieldDoesNotExist

from smart_agri.core.models import IdempotencyRecord
from smart_agri.core.api.permissions import FarmScopedPermission, user_farm_ids, _ensure_user_has_farm_access
from smart_agri.core.api.utils import _sync_pk_sequence
from smart_agri.accounts.models import FarmMembership

logger = logging.getLogger(__name__)

class DuplicateRequestError(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "تم اكتشاف طلب مكرر."
    default_code = "duplicate_request"


from smart_agri.core.services.idempotency import IdempotencyService, IdempotencyLocked, IdempotencyMismatch

class IdempotentCreateMixin:
    """
    Mixin to handle idempotent requests via Idempotency-Key header using V2 Service (Acquire-Then-Execute).
    """

    def _idempotency_required(self, request):
        return bool(getattr(self, "enforce_idempotency", False))

    def _get_idempotency_key(self, request):
        return request.META.get('HTTP_X_IDEMPOTENCY_KEY') or request.META.get('HTTP_IDEMPOTENCY_KEY')

    def create(self, request, *args, **kwargs):
        mutation = getattr(super(), 'create', None)
        if mutation is None:
            return Response({'detail': 'العملية غير مدعومة لهذا المورد.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return self._handle_idempotent_mutation(request, mutation, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        mutation = getattr(super(), 'update', None)
        if mutation is None:
            return Response({'detail': 'العملية غير مدعومة لهذا المورد.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return self._handle_idempotent_mutation(request, mutation, *args, **kwargs)


    def destroy(self, request, *args, **kwargs):
        mutation = getattr(super(), 'destroy', None)
        if mutation is None:
            return Response({'detail': 'العملية غير مدعومة لهذا المورد.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return self._handle_idempotent_mutation(request, mutation, *args, **kwargs)

    def _handle_idempotent_mutation(self, request, mutation_fn, *args, **kwargs):
        if not self._idempotency_required(request):
            return mutation_fn(request, *args, **kwargs)

        key = self._get_idempotency_key(request)
        if not key:
            return Response(
                {'detail': 'مطلوب ترويسة X-Idempotency-Key لضمان عدم تكرار العملية.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
             return Response(
                {'detail': 'يلزم تسجيل الدخول.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Resolve Farm ID if possible for scoping
        farm_id = request.data.get('farm') or request.query_params.get('farm') or kwargs.get('farm_pk')

        try:
             # 1. Acquire Lock
             record, is_replay, cached_response = IdempotencyService.acquire_lock(
                 key=key,
                 user=user,
                 method=request.method,
                 path=request.path,
                 body=request.data,
                 params=request.query_params,
                 farm_id=farm_id
             )

             # 2. Replay if already succeeded
             if is_replay and cached_response:
                 s_code, s_body = cached_response
                 return Response(s_body, status=s_code)

             # 3. Execute Mutation
             try:
                 # Wrap in atomic for consistency
                 with transaction.atomic():
                     response = mutation_fn(request, *args, **kwargs)
                 
                 # 4. Commit Success
                 if 200 <= getattr(response, 'status_code', 500) < 300:
                     obj_id = self._resolve_object_id(response, kwargs)
                     model_name = getattr(self, 'model_name', self.get_queryset().model.__name__)
                     
                     IdempotencyService.commit_success(
                         record=record,
                         response_status=response.status_code,
                         response_body=getattr(response, 'data', None),
                         object_id=obj_id,
                         model_name=model_name
                     )
                 else:
                     # 5. Commit Failure (retryable)
                     IdempotencyService.commit_failure(record)
                 
                 return response

             except (ValidationError, OperationalError, PermissionDenied) as e:
                 # 5. Commit Failure on Exception
                 logger.error(f"Mutation failed for key {key}: {e}", exc_info=True)
                 IdempotencyService.commit_failure(record)
                 raise

        except (IdempotencyLocked, IdempotencyMismatch) as e:
            return Response({'detail': str(e.detail)}, status=e.status_code)
        except (ValidationError, OperationalError, PermissionDenied) as e:
            logger.error(f"Idempotency internal error: {e}", exc_info=True)
            raise

    def _resolve_object_id(self, response=None, kwargs=None):
        data = getattr(response, 'data', None)
        if isinstance(data, dict):
            response_id = data.get('id')
            if response_id:
                return response_id
        lookup_url_kwarg = getattr(self, 'lookup_url_kwarg', None) or getattr(self, 'lookup_field', 'pk')
        if kwargs and lookup_url_kwarg in kwargs:
            return kwargs[lookup_url_kwarg]
        return ''

    def enforce_action_idempotency(self, request, farm_id=None):
        if not self._idempotency_required(request):
            return None, None, None

        key = self._get_idempotency_key(request)
        if not key:
             return None, None, Response(
                {'detail': 'مطلوب ترويسة X-Idempotency-Key.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        try:
            record, is_replay, cached_res = IdempotencyService.acquire_lock(
                key=key,
                user=user,
                method=request.method,
                path=request.path,
                body=request.data,
                params=request.query_params,
                farm_id=farm_id
            )
            if is_replay and cached_res:
                s_code, s_body = cached_res
                return key, record, Response(s_body, status=s_code)
            
            return key, record, None
            
        except (IdempotencyLocked, IdempotencyMismatch) as e:
            return None, None, Response({'detail': str(e.detail)}, status=e.status_code)

    def commit_action_idempotency(self, record, response, object_id=''):
        if not record:
            return
        
        if 200 <= response.status_code < 300:
             IdempotencyService.commit_success(
                 record=record,
                 response_status=response.status_code,
                 response_body=getattr(response, 'data', None),
                 object_id=object_id,
                 model_name=getattr(self, 'model_name', '')
             )
        else:
             IdempotencyService.commit_failure(record)

    # ── Backward-compatible underscore-prefixed wrappers ──
    # ViewSet @action methods call self._enforce_action_idempotency(request)
    # expecting a 2-tuple (key, error_response) return.
    def _enforce_action_idempotency(self, request, farm_id=None):
        """Returns (key, error_response). If idempotency not required, returns (None, None)."""
        if not self._idempotency_required(request):
            return None, None
        key, record, response = self.enforce_action_idempotency(request, farm_id)
        self._action_idempotency_record = record
        return key, response

    def _commit_action_idempotency(self, request, key, object_id='', response=None):
        """Commits the action idempotency record stored by _enforce_action_idempotency."""
        record = getattr(self, '_action_idempotency_record', None)
        if record and response:
            self.commit_action_idempotency(record, response, object_id=object_id)



class AuditedModelViewSet(IdempotentCreateMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, FarmScopedPermission]
    audit = True
    # [AGRI-GUARDIAN] Northern Yemen weak-network doctrine:
    # All mutation endpoints must be retry-safe by default.
    # ViewSets may opt-out explicitly by setting enforce_idempotency = False.
    enforce_idempotency = True

    def _get_requested_farm_id(self):
        """
        Normalize farm scoping query across `farm` and `farm_id`.
        Returns None when no explicit farm requested.
        """
        params = getattr(self.request, "query_params", {})
        candidate = params.get("farm_id") or params.get("farm")
        if candidate in (None, "", "null", "undefined"):
            return None
        return candidate

    def _enforce_mobile_request_id(self, serializer):
        request_id = serializer.validated_data.get('mobile_request_id')
        if not request_id:
            return

        model = getattr(getattr(serializer, 'Meta', None), 'model', None)
        if not model:
            return
        try:
            model._meta.get_field('mobile_request_id')
        except FieldDoesNotExist:
            return

        if model.objects.filter(mobile_request_id=request_id).exists():
            raise DuplicateRequestError(
                detail="تم اكتشاف عملية مكررة (mobile_request_id). تم تنفيذ هذا الطلب مسبقاً."
            )

    def _apply_farm_scope(self, queryset):
        user = getattr(self.request, 'user', None)
        model = getattr(queryset, 'model', None)
        if not model:
            return queryset

        try:
            model._meta.get_field('farm')
            has_direct_farm = True
        except FieldDoesNotExist:
            has_direct_farm = False

        if not user or user.is_superuser:
            # [AGRI-GUARDIAN §F-2] Audit superuser scope bypass for forensic traceability.
            if user and user.is_superuser:
                logger.info(
                    "ADMIN_BYPASS_AUDIT: superuser=%s accessed unscoped queryset model=%s",
                    user.username, model.__name__
                )
            requested = self._get_requested_farm_id()
            if has_direct_farm and requested and str(requested).lower() != 'all':
                return queryset.filter(farm_id=requested)
            return queryset

        if not has_direct_farm:
            return queryset

        farm_ids = user_farm_ids(user)
        if not farm_ids:
            return queryset.none()

        scoped = queryset.filter(farm_id__in=farm_ids)
        farm_param = self._get_requested_farm_id()
        if farm_param and str(farm_param).lower() != 'all':
            _ensure_user_has_farm_access(user, farm_param)
            scoped = scoped.filter(farm_id=farm_param)
        return scoped

    def get_queryset(self):
        queryset = super().get_queryset()
        return self._apply_farm_scope(queryset)

    def _log_action(self, action, instance, payload=None, old_payload=None, reason=""):
        if not self.audit:
            return
            
        try:
            from smart_agri.core.models import AuditLog
            import json
            from django.core.serializers.json import DjangoJSONEncoder
            
            user = self.request.user if (self.request and hasattr(self.request, 'user') and self.request.user.is_authenticated) else None
            model_name = instance._meta.object_name
            object_id = str(instance.pk)
            
            # Sanitize payloads to ensure Decimals and DateTimes are JSON serializable
            safe_new_payload = json.loads(json.dumps(payload or {}, cls=DjangoJSONEncoder))
            safe_old_payload = json.loads(json.dumps(old_payload or {}, cls=DjangoJSONEncoder))
            
            # [AGRI-GUARDIAN] Axis 20: Cryptographic non-repudiation
            from smart_agri.core.services.forensic_service import ForensicService
            proof = ForensicService.sign_transaction(
                agent=str(user.username if user else "anonymous"),
                action=action,
                payload=safe_new_payload
            )
            
            AuditLog.objects.create(
                actor=user,
                action=action,
                model=model_name,
                object_id=object_id,
                new_payload=safe_new_payload,
                old_payload=safe_old_payload,
                reason=reason or "",
                signature=proof.get('signature'),
            )
        except (ValidationError, OperationalError, PermissionDenied) as e:
            # [AGRI-GUARDIAN §F-3] Audit failure must be loud — production alerting
            # sidecars (Sentry, CloudWatch) MUST capture CRITICAL-level events.
            import logging
            logger = logging.getLogger(__name__)
            logger.critical(
                "AUDIT_INTEGRITY_ALERT: Failed to create AuditLog for %s on %s: %s",
                action, instance, e, exc_info=True
            )

    def perform_create(self, serializer):
        farm = serializer.validated_data.get('farm')
        if farm:
            _ensure_user_has_farm_access(self.request.user, getattr(farm, 'id', getattr(farm, 'pk', None)))
        self._enforce_mobile_request_id(serializer)
        super().perform_create(serializer)
        instance = serializer.instance
        self._log_action("create", instance, payload=serializer.data)

    def perform_update(self, serializer):
        farm = serializer.validated_data.get('farm') or getattr(serializer.instance, 'farm', None)
        if farm:
            _ensure_user_has_farm_access(self.request.user, getattr(farm, 'id', getattr(farm, 'pk', None)))
        # [AGRI-GUARDIAN] Capture state BEFORE mutation for forensic diff
        old_data = {}
        try:
            old_data = self.get_serializer(serializer.instance).data
        except (ValidationError, OperationalError, FieldDoesNotExist):
            old_data = {'pk': serializer.instance.pk}
        super().perform_update(serializer)
        instance = serializer.instance
        reason = self.request.data.get('audit_reason', '')
        self._log_action("update", instance, payload=serializer.data, old_payload=old_data, reason=reason)

    def perform_destroy(self, instance):
        # [AGRI-GUARDIAN] Capture full snapshot before deletion for forensic chain
        snapshot = {}
        try:
            if hasattr(self, 'get_serializer'):
                snapshot = self.get_serializer(instance).data
            else:
                 snapshot = {'pk': instance.pk, 'str': str(instance)}
        except (ValidationError, OperationalError, FieldDoesNotExist):
            snapshot = {'pk': instance.pk}

        reason = getattr(self.request, 'data', {}).get('audit_reason', '')
        super().perform_destroy(instance)
        self._log_action("delete", instance, payload=snapshot, reason=reason)
