from smart_agri.core.models import IdempotencyRecord
import logging
from django.core.exceptions import ValidationError
from django.db import OperationalError
from .idempotency import IdempotencyService, IdempotencyLocked, IdempotencyMismatch
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction

logger = logging.getLogger(__name__)

class IdempotentCreateMixin:
    """
    Mixin to handle idempotent requests via Idempotency-Key header using V2 Service (Acquire-Lock).
    """

    def _idempotency_required(self, request):
        return bool(getattr(self, "enforce_idempotency", False))

    def _get_idempotency_key(self, request):
        return request.META.get('HTTP_X_IDEMPOTENCY_KEY') or request.META.get('HTTP_IDEMPOTENCY_KEY')

    def create(self, request, *args, **kwargs):
        return self._handle_idempotent_mutation(request, super().create, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return self._handle_idempotent_mutation(request, super().update, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self._handle_idempotent_mutation(request, super().partial_update, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return self._handle_idempotent_mutation(request, super().destroy, *args, **kwargs)

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
        # Try finding it in params or user scope
        farm_id = request.data.get('farm') or request.query_params.get('farm')
        # If not found, maybe in view kwargs?
        if not farm_id and 'farm_pk' in kwargs:
             farm_id = kwargs['farm_pk']

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

             # 3. Execute Mutation (Atomic is handled inside mutation_fn usually, or we wrap here)
             # But acquire_lock already committed the IN_PROGRESS state.
             # Now we run the actual logic.
             try:
                 # We wrap in atomic to ensure mutation items are consistent
                 # But if mutation_fn has its own atomic, it nests fine.
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
                     # 5. Commit Failure (so it can be retried)
                     IdempotencyService.commit_failure(record)
                 
                 return response

             except (ValidationError, OperationalError, ValueError) as e:
                 # 5. Commit Failure on Exception
                 logger.error(f"Mutation failed for key {key}: {e}", exc_info=True)
                 IdempotencyService.commit_failure(record)
                 raise

        except IdempotencyLocked as e:
            return Response({'detail': str(e.detail)}, status=e.status_code)
        except IdempotencyMismatch as e:
            return Response({'detail': str(e.detail)}, status=e.status_code)
        except (ValidationError, OperationalError, ValueError) as e:
            logger.error(f"Idempotency internal error: {e}", exc_info=True)
            raise

    # Helpers stay mostly same
    def _resolve_object_id(self, response=None, kwargs=None):
        data = getattr(response, 'data', None)
        if isinstance(data, dict):
            response_id = data.get('id')
            if response_id:
                return response_id
        # Fallback to URL lookup
        lookup_url_kwarg = getattr(self, 'lookup_url_kwarg', None) or getattr(self, 'lookup_field', 'pk')
        if kwargs and lookup_url_kwarg in kwargs:
            return kwargs[lookup_url_kwarg]
        return ''

    # Replaces _enforce_action_idempotency and _commit_action_idempotency
    # used by custom actions.
    def enforce_action_idempotency(self, request, farm_id=None):
        """
        Manual hook for @action methods to use V2 service.
        Usage:
           key, record, response = self.enforce_action_idempotency(request)
           if response: return response
           ... do work ...
           self.commit_action_idempotency(record, result_response)
        """
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

    # ── Backward-compatible aliases for ViewSet @action methods ──
    # ViewSet actions call self._enforce_action_idempotency(request)
    # expecting (key, error_response) return pattern.
    def _enforce_action_idempotency(self, request, farm_id=None):
        """
        Backward-compatible wrapper. Returns (key, error_response).
        If idempotency is not required, returns (None, None) allowing
        the action to proceed without an idempotency key.
        """
        if not self._idempotency_required(request):
            return None, None

        key, record, response = self.enforce_action_idempotency(request, farm_id)
        # Store record for later commit
        self._action_idempotency_record = record
        return key, response

    def _commit_action_idempotency(self, request, key, object_id='', response=None):
        """
        Backward-compatible wrapper for committing action idempotency.
        """
        record = getattr(self, '_action_idempotency_record', None)
        if record and response:
            self.commit_action_idempotency(record, response, object_id=object_id)

