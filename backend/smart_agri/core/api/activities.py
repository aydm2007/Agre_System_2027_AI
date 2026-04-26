import logging
from datetime import date
from typing import Optional
from decimal import Decimal
from django.db import transaction, OperationalError

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from smart_agri.core.api.serializers import ActivitySerializer
from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.core.api.permissions import (
    _ensure_user_has_farm_access,
    _limit_queryset_to_user_farms,
)
from smart_agri.core.api.utils import (
    _clean_team_token,
    _sync_pk_sequence,
    _tokenize_team_field,
)
from smart_agri.core.di import container
from smart_agri.core.services.interfaces import IInventoryService
from smart_agri.core.models import Activity

logger = logging.getLogger(__name__)


class ActivityViewSet(AuditedModelViewSet):
    queryset = Activity.objects.filter(deleted_at__isnull=True).order_by('-id')
    serializer_class = ActivitySerializer
    model_name = "Activity"

    def _sync_tree_inventory(
        self,
        activity: Activity,
        *,
        delta_change: Optional[int] = None,
        previous_delta: Optional[int] = None,
        activity_tree_count_change: Optional[int] = None,
        previous_activity_tree_count: Optional[int] = None,
        previous_location=None,
        previous_variety=None,
    ):
        try:
            # [DI] Resolve Inventory Service via Container
            inventory_service = container.get(IInventoryService)
            
            inventory_service.record_event_from_activity(
                activity,
                user=getattr(self.request, "user", None),
                delta_change=delta_change,
                previous_delta=previous_delta,
                activity_tree_count_change=activity_tree_count_change,
                previous_activity_tree_count=previous_activity_tree_count,
                previous_location=previous_location,
                previous_variety=previous_variety,
            )
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") and exc.message_dict else exc.messages
            raise ValidationError(detail)
        except ValidationError:
            raise
        except (ValidationError, OperationalError) as exc:  # pragma: no cover - تسجيل وقائي
            logger.exception("Tree inventory reconciliation failed for activity %s", activity.pk, exc_info=exc)
            raise ValidationError({'detail': 'حدث خطأ أثناء تحديث مخزون الأشجار. يرجى مراجعة المسؤول.'})

    def get_queryset(self):
        qs = (
            Activity.objects.select_related(
                'log', 
                'log__farm', 
                'crop', 
                'task', 
                'asset', 
                'well_asset',
                'crop_variety',
                'product',
                'tree_loss_reason',
                'crop_plan',
                # نماذج التمديد للنمط متعدد الأشكال
                'harvest_details',
                'irrigation_details',
                'material_details',
                'machine_details',
            )
            .prefetch_related(
                'service_coverages',
                'service_coverages__crop_variety', 
                'service_coverages__location',
                'activity_locations__location'
            )
            .filter(deleted_at__isnull=True)
        )
        params = getattr(self.request, 'query_params', {})
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        farm_id = params.get('farm_id')
        location_id = params.get('location') or params.get('location_id')
        crop_id = params.get('crop_id')
        task_id = params.get('task_id')
        crop_plan_id = params.get('crop_plan') or params.get('crop_plan_id')
        log_id = params.get('log')

        if farm_id:
            qs = qs.filter(log__farm_id=farm_id)
        if location_id:
            qs = qs.filter(activity_locations__location_id=location_id).distinct()
        if start_date and end_date:
            qs = qs.filter(log__log_date__range=[start_date, end_date])
        if crop_id:
            qs = qs.filter(crop_id=crop_id)
        if task_id:
            qs = qs.filter(task_id=task_id)
        if crop_plan_id:
            qs = qs.filter(crop_plan_id=crop_plan_id)
        if log_id:
            qs = qs.filter(log_id=log_id)

        return _limit_queryset_to_user_farms(qs, self.request.user, 'log__farm_id__in')

    @action(detail=False, methods=['get'], url_path='defaults')
    def defaults(self, request):
        """
        [GEM 1]: Predictive Auto-Fill
        Returns the last used configuration (Provider, Asset, Hours) for a given Task + Location.
        """
        task_id = request.query_params.get('task') or request.query_params.get('task_id')
        location_id = request.query_params.get('location') or request.query_params.get('location_id')

        if not task_id or not location_id:
            return Response({})

        # Find the most recent activity (excluding deleted)
        last_activity = (
            Activity.objects.filter(
                task_id=task_id, 
                location_id=location_id, 
                deleted_at__isnull=True
            )
            .order_by('-log__log_date', '-created_at')
            .first()
        )

        if not last_activity:
            return Response({})

        # Safely access machine details if available
        machine_hours = None
        if hasattr(last_activity, 'machine_details'):
            machine_hours = last_activity.machine_details.machine_hours

        data = {
            # 'service_provider': last_activity.service_provider_id, # Field removed from model
            'asset': last_activity.asset_id,
            'well_asset': last_activity.well_asset_id,
            'days_spent': last_activity.days_spent,
            'machine_hours': machine_hours,
        }
        # Filter out None values to keep payload clean
        return Response({k: v for k, v in data.items() if v is not None})

    @action(detail=False, methods=["get"], url_path="team-suggestions")
    def team_suggestions(self, request):
        farm_param = request.query_params.get('farm_id') or request.query_params.get('farm')
        if not farm_param:
            return Response({'detail': 'معرف المزرعة مطلوب.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            farm_id = int(farm_param)
        except (TypeError, ValueError):
            return Response({'detail': 'معرف المزرعة غير صالح.'}, status=status.HTTP_400_BAD_REQUEST)

        _ensure_user_has_farm_access(request.user, farm_id)

        query = request.query_params.get('q') or request.query_params.get('query') or ''
        cleaned_query = _clean_team_token(query)
        normalized_query = cleaned_query.casefold() if cleaned_query else ''

        limit_param = request.query_params.get('limit')
        try:
            limit = int(limit_param) if limit_param is not None else 25
        except (TypeError, ValueError):
            limit = 25
        limit = max(1, min(limit, 100))

        rows = (
            Activity.objects.filter(log__farm_id=farm_id, deleted_at__isnull=True)
            .exclude(team__isnull=True)
            .exclude(team__exact='')
            .order_by('id')
            .values_list('team', flat=True)
        )

        aggregated = {}
        order_counter = 0

        for raw_value in rows:
            for token in _tokenize_team_field(raw_value):
                cleaned = _clean_team_token(token)
                if not cleaned:
                    continue
                key = cleaned.casefold()
                record = aggregated.get(key)
                if record:
                    record['count'] += 1
                else:
                    aggregated[key] = {'value': cleaned, 'count': 1, 'order': order_counter}
                    order_counter += 1

        suggestions = list(aggregated.values())
        if normalized_query:
            suggestions = [item for item in suggestions if item['value'].casefold().startswith(normalized_query)]

        suggestions.sort(key=lambda item: (-item['count'], item['order'], item['value']))

        payload = [item['value'] for item in suggestions[:limit]]
        return Response(payload)

    @action(detail=False, methods=['post'], url_path='bulk-sync')
    def bulk_sync(self, request):
        """
        [Offline Queue Hook]
        Receives a batch of activities from the OfflineProvider.
        """
        key, error_response = self._enforce_action_idempotency(request)
        if error_response:
            return error_response
        from smart_agri.core.services.activity_service import ActivityService
        
        # Expecting a list of activity payloads
        data = request.data
        if not isinstance(data, list):
            return Response({'error': 'Expected a list of activities'}, status=400)
            
        result = ActivityService.bulk_create_activities(request.user, data)
        
        if result.success:
            # Return list of IDs (or UUIDs) to confirm sync
            synced_ids = [a.uuid for a in result.data if hasattr(a, 'uuid')]
            first_id = str(synced_ids[0]) if synced_ids else ''
            response = Response({'synced_ids': synced_ids}, status=201)
            self._commit_action_idempotency(request, key, object_id=first_id, response=response)
            return response
        else:
            return Response({'error': result.message, 'details': result.errors}, status=400)

    def _assert_can_mutate(self, instance):
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            raise PermissionDenied("يجب تسجيل الدخول لتعديل النشاط.")
        if user.is_superuser or user.has_perm('core.change_activity') or user.has_perm('core.delete_activity'):
            return
        if instance.created_by_id != user.id:
            raise PermissionDenied("لا تملك صلاحية تعديل نشاط لم تقم بإنشائه.")
        today = timezone.localdate()
        log_date = getattr(instance.log, 'log_date', None)
        if isinstance(log_date, str):
            try:
                log_date = date.fromisoformat(log_date)
            except ValueError:
                log_date = None
        if log_date != today:
            raise PermissionDenied("لا يمكن تعديل الأنشطة السابقة، التعديل مسموح فقط لنفس اليوم.")

    def create(self, request, *args, **kwargs):
        """
        Override create to log validation failures (400) for debugging.
        """
        try:
            resp = super().create(request, *args, **kwargs)
        except ValidationError as e:
             import json
             logger.error('Activity create FAILED (ValidationError); request: %s; error: %s', 
                          json.dumps(request.data, default=str, ensure_ascii=False),
                          json.dumps(e.detail, default=str, ensure_ascii=False))
             raise e
        except (ValidationError, OperationalError, ValueError) as e:
             logger.exception("Activity create CRASHED")
             raise e

        status_code = getattr(resp, 'status_code', None)
        if status_code and int(status_code) >= 400:
            import json
            try:
                logger.error('Activity create returned %s; request data: %s; response: %s',
                                status_code,
                                json.dumps(request.data, default=str, ensure_ascii=False),
                                json.dumps(getattr(resp, 'data', resp), default=str, ensure_ascii=False),
                )
            except (ValidationError, OperationalError):
                logger.exception('Failed to log activity validation failure')
        return resp

    def perform_create(self, serializer):
        from smart_agri.core.services.activity_service import ActivityService
        # استخدام غلاف معاملة بسيط لمنطق viewset،
        # لكن ActivityService يتعامل مع منطق العمل الأساسي للمعاملة.
        validated_data = serializer.validated_data
        
        # Access control checks
        log = validated_data.get('log')
        if log:
            _ensure_user_has_farm_access(self.request.user, getattr(log, 'farm_id', None))
        well_asset = validated_data.get('well_asset')
        if well_asset:
            _ensure_user_has_farm_access(self.request.user, getattr(well_asset, 'farm_id', None))

        # نحتاج إلى بناء قاموس البيانات الكامل للخدمة
        # usually serializer.save() does this, but we want to delegate to Service.
        # لذلك نستخدم validated_data مباشرة.
        
        # Service call
        try:
            result = ActivityService.maintain_activity(
                user=self.request.user,
                data=validated_data,
                activity_id=None
            )
        except IntegrityError:
             _sync_pk_sequence(Activity)
             result = ActivityService.maintain_activity(
                user=self.request.user,
                data=validated_data,
                activity_id=None
            )
        if not result.success or result.data is None:
            errors = result.errors or {"detail": result.message or "Activity creation failed"}
            if isinstance(errors, dict) and "items" in errors and isinstance(errors["items"], list):
                errors = {"items": {"shortages": errors["items"]}}
            raise ValidationError(errors)
        serializer.instance = result.data

        # [AGRI-GUARDIAN §Axis-14] Auto-trigger schedule variance check.
        # Fires after every successful activity creation to detect out-of-window activities.
        try:
            from smart_agri.core.services.schedule_variance_service import ScheduleVarianceService
            ScheduleVarianceService.check_schedule_variance(
                activity=result.data,
                user=self.request.user,
            )
        except (ValueError, TypeError, LookupError, AttributeError, ImportError, OperationalError, RuntimeError) as exc:
            logger.warning(
                "Schedule variance check failed for activity %s: %s",
                result.data.pk, exc,
            )

    def perform_update(self, serializer):
        from smart_agri.core.services.activity_service import ActivityService
        
        validated_data = serializer.validated_data
        instance = serializer.instance
        self._assert_can_mutate(instance)
        
        # Access Check
        log = validated_data.get('log') or instance.log
        if log:
            _ensure_user_has_farm_access(self.request.user, getattr(log, 'farm_id', None))
            
        # Service Call
        # Note: serializer.validated_data only contains updated fields.
        # maintain_activity expects a data dict to update.
        # If 'items' is in validated_data, Service will handle replacement.
        result = ActivityService.maintain_activity(
            user=self.request.user,
            data=validated_data,
            activity_id=instance.pk
        )
        if not result.success:
            errors = result.errors or {"detail": result.message or "Activity update failed"}
            if isinstance(errors, dict) and "items" in errors and isinstance(errors["items"], list):
                errors = {"items": {"shortages": errors["items"]}}
            raise ValidationError(errors)

    def perform_destroy(self, instance):
        from smart_agri.core.services.activity_service import ActivityService
        self._assert_can_mutate(instance)
        ActivityService.delete_activity(user=self.request.user, activity=instance)


