from datetime import datetime
from uuid import UUID

from django.db import transaction, DatabaseError, IntegrityError
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access
from smart_agri.core.api.viewsets.base import IdempotentCreateMixin
from smart_agri.core.models import DailyLog, SyncConflictDLQ, SyncRecord
from smart_agri.core.models.farm import Farm
from smart_agri.core.models.settings import Supervisor
from smart_agri.core.models.task import Task
from smart_agri.core.models import CropPlan
from smart_agri.core.services.activity_service import ActivityService
from smart_agri.core.api.viewsets.offline_runtime import _resolve_or_create_daily_log_for_replay


BACKEND_OWNED_ACTIVITY_COST_FIELDS = (
    "cost_materials",
    "cost_labor",
    "cost_machinery",
    "cost_overhead",
    "cost_wastage",
    "cost_total",
)


def _scrub_backend_owned_activity_fields(payload):
    cleaned = dict(payload or {})
    for field_name in BACKEND_OWNED_ACTIVITY_COST_FIELDS:
        cleaned.pop(field_name, None)
    return cleaned


def _valid_uuid_or_none(*values):
    for value in values:
        if value in (None, ""):
            continue
        try:
            return str(UUID(str(value)))
        except (TypeError, ValueError):
            continue
    return None


class OfflineDailyLogReplayViewSet(IdempotentCreateMixin, viewsets.ViewSet):
    queryset = SyncRecord.objects.none()
    permission_classes = [permissions.IsAuthenticated]
    enforce_idempotency = True
    model_name = "OfflineDailyLogReplay"
    http_method_names = ["post", "head", "options"]

    def create(self, request):
        farm_id = request.data.get("farm_id") or request.data.get("farm") if isinstance(request.data, dict) else None
        key, error_response = self._enforce_action_idempotency(request, farm_id=farm_id)
        if error_response:
            return error_response
        response = self._create_impl(request)
        object_id = ""
        if isinstance(getattr(response, "data", None), dict):
            object_id = str(response.data.get("activity_id") or response.data.get("uuid") or "")
        self._commit_action_idempotency(request, key, object_id=object_id, response=response)
        return response

    def _create_impl(self, request):
        data = request.data or {}
        payload_uuid = data.get("uuid")
        idempotency_key = data.get("idempotency_key")
        farm_id = data.get("farm_id") or data.get("farm")
        supervisor_id = data.get("supervisor_id")
        client_seq = data.get("client_seq")
        device_timestamp = data.get("device_timestamp")
        draft_uuid = data.get("draft_uuid")
        lookup_snapshot_version = data.get("lookup_snapshot_version")
        task_contract_snapshot = data.get("task_contract_snapshot")
        device_id = (
            data.get("device_id")
            or data.get("client_metadata", {}).get("device_id")
            or f"user-{request.user.id}"
        )
        log_payload = data.get("log") or data.get("logPayload") or {}
        activity_payload = data.get("activity") or data.get("activityPayload") or {}

        if not payload_uuid:
            raise ValidationError({"uuid": "uuid مطلوب للمزامنة الذرية."})
        if not idempotency_key:
            raise ValidationError({"idempotency_key": "idempotency_key مطلوب."})
        if farm_id in (None, ""):
            raise ValidationError({"detail": "farm_id مطلوب."})
        if client_seq in (None, ""):
            raise ValidationError({"client_seq": "client_seq مطلوب."})

        _ensure_user_has_farm_access(request.user, farm_id)

        farm = Farm.objects.get(pk=farm_id)
        supervisor = None
        if supervisor_id not in (None, ""):
            supervisor = Supervisor.objects.get(pk=supervisor_id, farm=farm)

        try:
            client_seq = int(client_seq)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"client_seq": "client_seq يجب أن يكون رقمًا صحيحًا."}) from exc

        parsed_device_timestamp = None
        if device_timestamp:
            try:
                parsed_device_timestamp = datetime.fromisoformat(str(device_timestamp).replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError({"device_timestamp": "صيغة device_timestamp غير صالحة."}) from exc

        existing_record = (
            SyncRecord.objects.filter(
                user=request.user,
                category=SyncRecord.CATEGORY_DAILY_LOG,
                reference=payload_uuid,
            )
            .order_by("-updated_at")
            .first()
        )
        if existing_record and existing_record.status == SyncRecord.STATUS_SUCCESS:
            response_payload = existing_record.payload.get("response") if isinstance(existing_record.payload, dict) else None
            if response_payload:
                return Response(response_payload, status=status.HTTP_200_OK)

        max_seq = (
            SyncRecord.objects.filter(
                user=request.user,
                category=SyncRecord.CATEGORY_DAILY_LOG,
                status=SyncRecord.STATUS_SUCCESS,
                farm=farm,
            )
            .filter(payload__device_id=device_id, payload__supervisor_id=getattr(supervisor, "id", None))
            .values_list("payload__client_seq", flat=True)
        )
        max_processed_seq = max((int(value) for value in max_seq if value is not None), default=0)
        if client_seq > max_processed_seq + 1:
            SyncConflictDLQ.objects.create(
                farm=farm,
                actor=request.user,
                conflict_type="STALE_VERSION",
                conflict_reason=(
                    f"Out-of-order replay detected for device={device_id}. "
                    f"Expected next seq {max_processed_seq + 1}, got {client_seq}."
                ),
                endpoint=request.path,
                http_method=request.method,
                request_payload=data,
                idempotency_key=idempotency_key,
                device_timestamp=parsed_device_timestamp,
            )
            raise ValidationError(
                {
                    "client_seq": (
                        f"الترتيب غير صالح. المتوقع {max_processed_seq + 1}، "
                        f"والمرسل {client_seq}."
                    )
                }
            )

        try:
            with transaction.atomic():
                log_date = log_payload.get("log_date") or log_payload.get("date")
                if not log_date:
                    raise ValidationError({"log.log_date": "تاريخ السجل اليومي مطلوب."})

                daily_log, _created = _resolve_or_create_daily_log_for_replay(
                    farm=farm,
                    supervisor=supervisor,
                    log_date=log_date,
                    actor=request.user,
                    parsed_device_timestamp=parsed_device_timestamp,
                    log_payload=log_payload,
                )

                activity_input = _scrub_backend_owned_activity_fields(activity_payload)
                if "items" not in activity_input and "items_payload" in activity_input:
                    activity_input["items"] = activity_input.get("items_payload")
                if "location_ids" not in activity_input and "locations" in activity_input:
                    activity_input["location_ids"] = activity_input.get("locations")
                
                if "location_ids" not in activity_input and "locations" not in activity_input:
                    task_id = activity_input.get("task_id") or activity_input.get("task")
                    if task_id:
                        task_obj = Task._base_manager.filter(pk=task_id).select_related("crop").first()
                        if task_obj and getattr(task_obj, "crop", None):
                            active_plan = CropPlan.objects.filter(
                                farm=farm,
                                crop=task_obj.crop,
                                status__iexact="active",
                                deleted_at__isnull=True
                            ).first()
                            if active_plan:
                                plan_locations = list(active_plan.locations.values_list("id", flat=True))
                                if plan_locations:
                                    activity_input["location_ids"] = plan_locations

                activity_input["log"] = daily_log
                activity_input["log_id"] = daily_log.id
                activity_uuid_key = _valid_uuid_or_none(idempotency_key, payload_uuid)
                if activity_uuid_key:
                    activity_input["idempotency_key"] = activity_uuid_key
                activity_input["device_timestamp"] = parsed_device_timestamp

                result = ActivityService.maintain_activity(request.user, activity_input, activity_id=None)
                if not result.success or result.data is None:
                    raise ValidationError(result.errors or {"detail": result.message or "تعذر ترحيل النشاط."})

                response_payload = {
                    "uuid": payload_uuid,
                    "draft_uuid": draft_uuid,
                    "log_id": daily_log.id,
                    "activity_id": result.data.id,
                    "client_seq": client_seq,
                    "status": "synced",
                }
                sync_record, _ = SyncRecord.objects.get_or_create(
                    user=request.user,
                    category=SyncRecord.CATEGORY_DAILY_LOG,
                    reference=payload_uuid,
                    defaults={"farm": farm},
                )
                sync_record.farm = farm
                sync_record.status = SyncRecord.STATUS_SUCCESS
                sync_record.payload = {
                    "device_id": device_id,
                    "client_seq": client_seq,
                    "draft_uuid": draft_uuid,
                    "supervisor_id": getattr(supervisor, "id", None),
                    "lookup_snapshot_version": lookup_snapshot_version,
                    "task_contract_snapshot": task_contract_snapshot,
                    "response": response_payload,
                }
                sync_record.last_error_message = ""
                sync_record.last_attempt_at = timezone.now()
                sync_record.attempt_count = (sync_record.attempt_count or 0) + 1
                sync_record.log_date = daily_log.log_date
                sync_record.save()
        except (ValidationError, PermissionDenied) as exc:
            SyncConflictDLQ.objects.create(
                farm=farm,
                actor=request.user,
                conflict_type="VALIDATION_FAILURE",
                conflict_reason=f"Activity replay validation failed: {str(exc)}",
                endpoint=request.path,
                http_method=request.method,
                request_payload=data,
                idempotency_key=idempotency_key,
                device_timestamp=parsed_device_timestamp,
            )
            raise
        except (DatabaseError, IntegrityError) as exc:
            SyncConflictDLQ.objects.create(
                farm=farm,
                actor=request.user,
                conflict_type="DATABASE_ERROR",
                conflict_reason=f"Activity replay database error: {str(exc)}",
                endpoint=request.path,
                http_method=request.method,
                request_payload=data,
                idempotency_key=idempotency_key,
                device_timestamp=parsed_device_timestamp,
            )
            raise

        return Response(response_payload, status=status.HTTP_201_CREATED)
