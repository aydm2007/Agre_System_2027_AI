"""
Log ViewSets (Daily, Audit, Harvest, Sync)
"""
import uuid
from typing import Any
from django.db import IntegrityError, DatabaseError, OperationalError
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied
from django.db.models import Prefetch, Exists, OuterRef, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from smart_agri.core.models import (
    DailyLog, AuditLog, Attachment, SyncRecord, 
    # HarvestLog, 
    # HarvestLot -- Removed duplicate
    Activity, Farm
)
from smart_agri.core.api.serializers import (
    DailyLogSerializer, AuditLogSerializer, AttachmentSerializer, 
    SyncRecordSerializer, 
    # HarvestLogSerializer, 
    # HarvestLotSerializer -- Removed duplicate
    ActivitySerializer
)
from smart_agri.core.api.permissions import (
    user_farm_ids, 
    _ensure_user_has_farm_access, 
    _user_is_farm_manager,
    _limit_queryset_to_user_farms
)
from smart_agri.core.api.utils import _coerce_int, _sync_pk_sequence
from .base import AuditedModelViewSet

import logging
logger = logging.getLogger(__name__)

from smart_agri.core.models.log import MaterialVarianceAlert
from smart_agri.core.api.serializers.daily_log import MaterialVarianceAlertSerializer

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().order_by("-timestamp")
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class AttachmentViewSet(AuditedModelViewSet):
    queryset = Attachment.objects.all().filter(deleted_at__isnull=True).order_by("-created_at")
    serializer_class = AttachmentSerializer
    model_name = "Attachment"

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        if not user or user.is_superuser:
            return qs
        farm_ids = user_farm_ids(user)
        if not farm_ids:
            return qs.none()
        activity_subquery = Activity.objects.filter(
            attachment_id=OuterRef('pk'),
            log__farm_id__in=farm_ids
        )
        return qs.filter(Exists(activity_subquery))
    def perform_create(self, serializer):
        instance = serializer.save()
        if not instance.name and instance.file:
            instance.name = getattr(instance.file, "name", "")
            instance.save(update_fields=["name", "updated_at"])



class DailyLogViewSet(AuditedModelViewSet):
    queryset = DailyLog.objects.all().filter(deleted_at__isnull=True).order_by("-log_date","-id")
    serializer_class = DailyLogSerializer
    model_name = "DailyLog"

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _limit_queryset_to_user_farms(qs, self.request.user, 'farm_id__in')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status__iexact=status_filter)

        product_id = self.request.query_params.get('product') or self.request.query_params.get('product_id')
        if product_id:
            qs = qs.filter(product_id=product_id)

        crop_id = self.request.query_params.get('crop') or self.request.query_params.get('crop_id')
        if crop_id:
            qs = qs.filter(crop_id=crop_id)

        date_from = self.request.query_params.get('log_date__gte')
        if date_from:
            parsed_from = parse_date(date_from)
            if not parsed_from:
                raise ValidationError({'log_date__gte': 'Invalid date format. Use YYYY-MM-DD.'})
            qs = qs.filter(log_date__gte=parsed_from)

        date_to = self.request.query_params.get('log_date__lte')
        if date_to:
            parsed_to = parse_date(date_to)
            if not parsed_to:
                raise ValidationError({'log_date__lte': 'Invalid date format. Use YYYY-MM-DD.'})
            qs = qs.filter(log_date__lte=parsed_to)

        return qs

    def create(self, request, *args, **kwargs):
        """
        Override create with get-or-create semantics to prevent orphaned Draft stacking.

        When the Activity POST fails after the DailyLog is created, retrying normally
        creates another empty Draft. Instead, we return the oldest existing Draft for
        the same farm+date so the Activity can be linked to it.
        """
        farm_id = request.data.get('farm') or request.data.get('farm_id')
        log_date = request.data.get('log_date') or request.data.get('date')

        if farm_id and log_date:
            try:
                existing = DailyLog.objects.filter(
                    farm_id=farm_id,
                    log_date=log_date,
                    status=DailyLog.STATUS_DRAFT,
                    deleted_at__isnull=True,
                ).order_by('id').first()
                if existing:
                    serializer = self.get_serializer(existing)
                    return Response(serializer.data, status=status.HTTP_200_OK)
            except (DatabaseError, OperationalError, ValueError, TypeError):
                pass  # Fallback to normal create if lookup fails

        try:
            resp = super().create(request, *args, **kwargs)
        except ValidationError as e:
             import json
             logger.error('DailyLog create FAILED (ValidationError); request: %s; error: %s',
                          json.dumps(request.data, default=str, ensure_ascii=False),
                          json.dumps(e.detail, default=str, ensure_ascii=False))
             raise e
        except (ValidationError, OperationalError, ValueError) as e:
             logger.exception("DailyLog create CRASHED")
             raise e

        status_code = getattr(resp, 'status_code', None)
        if status_code and int(status_code) >= 400:
            try:
                import json
                try:
                    logger.error('DailyLog create returned %s; request data: %s; response: %s',
                                 status_code,
                                 json.dumps(request.data, default=str, ensure_ascii=False),
                                 json.dumps(getattr(resp, 'data', resp), default=str, ensure_ascii=False),
                    )
                except (ValidationError, OperationalError):
                    logger.error('DailyLog create returned %s; failed to serialize/log', status_code, exc_info=True)
            except (ValidationError, OperationalError):
                logger.exception('Failed to log daily log validation failure')
        return resp

    def _assert_can_mutate(self, instance):
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            raise PermissionDenied("يجب تسجيل الدخول.")
        if user.is_superuser or user.has_perm('core.change_dailylog') or user.has_perm('core.delete_dailylog'):
            return
        if instance.created_by_id != user.id:
            raise PermissionDenied("لا تملك صلاحية تعديل سجل لم تقم بإنشائه.")
        # Round 14: Early Morning Lockout Fix
        # Use Local Time, not UTC
        today = timezone.localtime(timezone.now()).date()
        if instance.log_date != today:
            raise PermissionDenied("لا يمكن تعديل السجلات السابقة.")

    def _can_mutate(self, instance):
        try:
            self._assert_can_mutate(instance)
        except PermissionDenied:
            return False
        return True

    @action(detail=False, methods=['get'], url_path='day-summary')
    def day_summary(self, request):
        date_value = request.query_params.get('date')
        if date_value:
            try:
                target_date = parse_date(date_value)
            except (TypeError, ValueError):
                target_date = None
            if not target_date:
                return Response(
                    {'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = timezone.now().date()

        farm_param = request.query_params.get('farm') or request.query_params.get('farm_id')
        farm_id = _coerce_int(farm_param)
        if farm_param and farm_id is None:
            return Response(
                {'detail': 'Invalid farm ID.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        activities_prefetch = Prefetch(
            'activities',
            queryset=Activity.objects.filter(deleted_at__isnull=True).select_related(
                'crop', 'task', 'asset'
            ).prefetch_related('locations').order_by('-created_at'),
            to_attr='prefetched_active_activities'
        )

        queryset = self.get_queryset().filter(log_date=target_date)
        if farm_id is not None:
            queryset = queryset.filter(farm_id=farm_id)
        
        logs = queryset.prefetch_related(
            activities_prefetch,
            'activities__service_coverages__crop_variety',
            'activities__service_coverages__location',
        )
        payload = []
        for log in logs:
            try:
                farm_obj = log.farm
            except Farm.DoesNotExist:
                farm_obj = None

            if log.farm_id is not None:
                farm_data = {
                    'id': log.farm_id,
                    'name': getattr(farm_obj, 'name', None),
                }
            else:
                farm_data = None

            activities = getattr(log, 'prefetched_active_activities', [])
            activities_data = ActivitySerializer(
                activities, 
                many=True, 
                context={'request': request, 'skip_context_fields': True}
            ).data
            payload.append({
                'id': log.id,
                'farm': farm_data,
                'log_date': log.log_date,
                'notes': log.notes,
                'created_by': log.created_by_id,
                'status': log.status,
                'can_edit': self._can_mutate(log),
                'activities': activities_data,
            })
        return Response({'date': target_date, 'logs': payload})

    def perform_create(self, serializer):
        farm = serializer.validated_data.get('farm')
        if farm:
            _ensure_user_has_farm_access(self.request.user, getattr(farm, 'id', getattr(farm, 'pk', None)))
        try:
            serializer.save(created_by=self.request.user, updated_by=self.request.user)
        except IntegrityError:
            _sync_pk_sequence(DailyLog)
            try:
                serializer.save(created_by=self.request.user, updated_by=self.request.user)
            except IntegrityError:
                raise ValidationError({'detail': 'تعذر إنشاء السجل بسبب تعارض قاعدة البيانات أو تكرار المعرف.'})

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance is not None:
            self._assert_can_mutate(instance)
        farm = serializer.validated_data.get('farm') or serializer.instance.farm
        if farm:
            _ensure_user_has_farm_access(self.request.user, getattr(farm, 'id', getattr(farm, 'pk', None)))
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        self._assert_can_mutate(instance)
        super().perform_destroy(instance)

    def _map_action_exception(self, exc, action_name, pk):
        if isinstance(exc, (PermissionDenied, DjangoPermissionDenied)):
            detail = getattr(exc, "detail", None) or str(exc) or "ليس لديك صلاحية لتنفيذ هذا الإجراء."
            return Response({'detail': detail}, status=status.HTTP_403_FORBIDDEN)

        if isinstance(exc, (ValidationError, DjangoValidationError)):
            detail = exc.detail if hasattr(exc, 'detail') else str(exc)
            return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(exc, (IntegrityError, DatabaseError)):
            logger.exception("%s action database failure for log %s", action_name, pk)
            return Response(
                {'detail': 'تعذر إكمال العملية بسبب خطأ قاعدة بيانات. حاول لاحقًا.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        logger.exception("%s action crashed for log %s", action_name, pk)
        return Response(
            {'detail': 'حدث خطأ داخلي غير متوقع. يرجى المحاولة لاحقًا.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        from smart_agri.core.services.log_approval_service import LogApprovalService
        log = self.get_object()
        try:
            LogApprovalService.submit_log(request.user, log)
        except (ValidationError, OperationalError, ValueError) as exc:
            return self._map_action_exception(exc, "submit", pk)
        response = Response({'status': 'submitted'})
        self._commit_action_idempotency(request, key, object_id=str(log.id), response=response)
        return response

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        from smart_agri.core.services.log_approval_service import LogApprovalService
        from smart_agri.core.services.variance import compute_log_variance
        log = self.get_object()

        # [AGRI-GUARDIAN Axis 8] Always re-compute and persist variance_status
        # BEFORE the atomic approve_log() call.  Activities may have changed
        # since submit, so we must refresh.  This save is committed immediately
        # — if approve_log raises ValidationError its @transaction.atomic rolls
        # back, but variance_status stays saved for the frontend.
        variance = compute_log_variance(log)
        log.variance_status = variance["status"]
        log.save(update_fields=["variance_status", "updated_at"])

        try:
            LogApprovalService.approve_log(request.user, log)
        except (ValidationError, OperationalError, ValueError) as exc:
            return self._map_action_exception(exc, "approve", pk)
        self._log_action("approve", log, payload={"status": "approved"})
        response = Response({'status': 'approved'})
        self._commit_action_idempotency(request, key, object_id=str(log.id), response=response)
        return response

    @action(detail=True, methods=['post'], url_path='warning-note')
    def warning_note(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        from smart_agri.core.services.log_approval_service import LogApprovalService
        log = self.get_object()
        note = request.data.get('note', '')
        try:
            LogApprovalService.note_warning(request.user, log, note)
        except (ValidationError, OperationalError, ValueError) as exc:
            return self._map_action_exception(exc, "warning_note", pk)
        response = Response({'status': 'warning_noted'})
        self._commit_action_idempotency(request, key, object_id=str(log.id), response=response)
        return response

    @action(detail=True, methods=['post'], url_path='approve-variance')
    def approve_variance(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        from smart_agri.core.services.log_approval_service import LogApprovalService
        log = self.get_object()
        note = request.data.get('note', '')
        try:
            LogApprovalService.approve_variance(request.user, log, note)
        except (ValidationError, OperationalError, ValueError) as exc:
            return self._map_action_exception(exc, "approve_variance", pk)
        response = Response({'status': 'variance_approved'})
        self._commit_action_idempotency(request, key, object_id=str(log.id), response=response)
        return response

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        from smart_agri.core.services.log_approval_service import LogApprovalService
        log = self.get_object()
        reason = request.data.get('reason', '')
        try:
            LogApprovalService.reject_log(request.user, log, reason)
        except (ValidationError, OperationalError, ValueError) as exc:
            return self._map_action_exception(exc, "reject", pk)
        response = Response({'status': 'rejected'})
        self._commit_action_idempotency(request, key, object_id=str(log.id), response=response)
        return response

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        from smart_agri.core.services.log_approval_service import LogApprovalService
        log = self.get_object()
        try:
            LogApprovalService.reopen_log(request.user, log)
        except (ValidationError, OperationalError, ValueError) as exc:
            return self._map_action_exception(exc, "reopen", pk)
        response = Response({'status': 'draft', 'message': 'تم إعادة فتح السجل ورده كمسودة.'})
        self._commit_action_idempotency(request, key, object_id=str(log.id), response=response)
        return response


    @action(detail=False, methods=['get'], url_path='available-varieties')
    def available_varieties(self, request):
        """
        [AGRI-GUARDIAN] Axis 11 Compliance: Location-Aware Variety Selection
        Returns the union of varieties from LocationTreeStock for given locations.
        """
        location_ids_raw = request.query_params.get('location_ids', '')
        if not location_ids_raw:
            return Response({'detail': 'location_ids parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            location_ids = [int(x.strip()) for x in location_ids_raw.split(',') if x.strip()]
        except ValueError:
            return Response({'detail': 'Invalid location_ids format.'}, status=status.HTTP_400_BAD_REQUEST)

        # Tenant isolation
        farm_ids = user_farm_ids(request.user)
        if not farm_ids and not request.user.is_superuser:
            return Response([])

        from smart_agri.core.models.tree import LocationTreeStock
        stocks = LocationTreeStock.objects.filter(
            location_id__in=location_ids,
            deleted_at__isnull=True
        )
        if not request.user.is_superuser:
            stocks = stocks.filter(location__farm_id__in=farm_ids)
            
        stocks = stocks.select_related('crop_variety', 'crop_variety__crop', 'location')
        
        # Aggregate results
        varieties = {}
        for s in stocks:
            vid = s.crop_variety_id
            if vid not in varieties:
                varieties[vid] = {
                    'id': vid,
                    'name': s.crop_variety.name,
                    'crop_id': s.crop_variety.crop_id,
                    'crop_name': s.crop_variety.crop.name,
                    'scientific_name': getattr(s.crop_variety, 'scientific_name', ''),
                    'total_trees': 0,
                    'location_count': 0,
                    'locations': []
                }
            varieties[vid]['total_trees'] += s.current_tree_count
            varieties[vid]['location_count'] += 1
            varieties[vid]['locations'].append({
                'location_id': s.location_id,
                'location_name': s.location.name,
                'tree_count': s.current_tree_count
            })
            
        return Response(list(varieties.values()))

    @action(detail=False, methods=['get'], url_path='location-tree-stock-summary')
    def location_tree_stock_summary(self, request):
        """
        [AGRI-GUARDIAN] Axis 11 Compliance: Tree Census Dashboard Source
        """
        farm_ids = user_farm_ids(request.user)
        if not farm_ids and not request.user.is_superuser:
            return Response([])

        from smart_agri.core.models.tree import LocationTreeStock
        stocks = LocationTreeStock.objects.filter(
            deleted_at__isnull=True
        )
        if not request.user.is_superuser:
            stocks = stocks.filter(location__farm_id__in=farm_ids)
            
        data = stocks.values(
            'location_id', 'location__name', 'crop_variety_id', 'crop_variety__name', 'current_tree_count'
        )
        return Response(list(data))


class SyncRecordViewSet(AuditedModelViewSet):
    serializer_class = SyncRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = SyncRecord.objects.select_related('farm').order_by('-updated_at')

    def get_queryset(self):
        qs = self.queryset
        status_filter = self.request.query_params.get('status')
        user = self.request.user
        if not user.is_superuser and not _user_is_farm_manager(user):
            qs = qs.filter(user=user)
        else:
            farm_ids = user_farm_ids(user)
            if farm_ids:
                qs = qs.filter(Q(user=user) | Q(farm_id__in=farm_ids))
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        farm = serializer.validated_data.get('farm')
        if farm:
            _ensure_user_has_farm_access(self.request.user, getattr(farm, 'id', getattr(farm, 'pk', None)))
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        farm = serializer.validated_data.get('farm') or (instance.farm if instance else None)
        if farm:
            _ensure_user_has_farm_access(self.request.user, getattr(farm, 'id', getattr(farm, 'pk', None)))
        serializer.save()

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        category = data.get('category') or SyncRecord.CATEGORY_DAILY_LOG
        reference = data.get('reference') or str(uuid.uuid4())
        status_value = data.get('status') or SyncRecord.STATUS_PENDING
        payload = data.get('payload') or {}
        log_date = data.get('log_date')
        farm_id = data.get('farm') or data.get('farm_id')
        message = data.get('message') or data.get('detail') or ''

        farm = None
        if farm_id:
            farm = Farm.objects.filter(pk=farm_id).first()
            if farm:
                _ensure_user_has_farm_access(request.user, farm.id)

        record, created = SyncRecord.objects.get_or_create(
            user=request.user,
            category=category,
            reference=reference,
            defaults={
                'status': status_value,
                'payload': payload,
                'log_date': log_date,
                'farm': farm,
            },
        )

        record.status = status_value
        record.payload = payload
        record.log_date = log_date
        record.farm = farm

        if status_value == SyncRecord.STATUS_FAILED:
            record.attempt_count = (record.attempt_count or 0) + 1
            record.last_error_message = message or record.last_error_message
            record.last_attempt_at = timezone.now()
        elif status_value == SyncRecord.STATUS_SUCCESS:
            record.last_error_message = ''
            record.last_attempt_at = timezone.now()
            if not record.attempt_count:
                record.attempt_count = 1
        else:
            if message:
                record.last_error_message = message

        record.save()
        serializer = self.get_serializer(record)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MaterialVarianceAlertViewSet(AuditedModelViewSet):
    """
    [AGRI-GUARDIAN] Axis 6 / Protocol III Validation:
    Supplies the Variance Alerts Dashboard with actionable divergence incidents.
    """
    serializer_class = MaterialVarianceAlertSerializer
    model_name = "MaterialVarianceAlert"

    def get_queryset(self):
        qs = MaterialVarianceAlert.objects.select_related(
            'log', 'log__farm', 'log__supervisor', 'crop_plan', 'item'
        ).all()
        
        farm_ids = user_farm_ids(self.request.user)
        if not self.request.user.is_superuser and farm_ids:
            qs = qs.filter(log__farm_id__in=farm_ids)
            
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        # [AGRI-GUARDIAN] URL Filters
        farm_filter = self.request.query_params.get('farm')
        location_filter = self.request.query_params.get('location')
        crop_filter = self.request.query_params.get('crop')

        if farm_filter:
            qs = qs.filter(log__farm_id=farm_filter)
        if location_filter:
            qs = qs.filter(log__activities__locations__id=location_filter).distinct()
        if crop_filter:
            qs = qs.filter(crop_plan__crop_id=crop_filter)
            
        return qs.order_by('-created_at')

    def _assert_can_mutate(self, instance):
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            raise PermissionDenied("يجب تسجيل الدخول.")
        if not (user.is_superuser or user.has_perm('core.change_materialvariancealert')):
            raise PermissionDenied("لا تملك صلاحية تعديل التنبيهات.")
