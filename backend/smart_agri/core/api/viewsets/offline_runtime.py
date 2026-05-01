import logging
from datetime import datetime, timedelta

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from smart_agri.core.api.permissions import (
    _ensure_user_has_farm_access,
    _limit_queryset_to_user_farms,
    _user_is_farm_manager,
    user_farm_ids,
)
from smart_agri.core.api.serializers import (
    CustodyIssueSerializer,
    CustodyTransitionSerializer,
    HarvestLotSerializer,
    OfflineSyncQuarantineSerializer,
    SyncConflictDLQSerializer,
    SyncRecordSerializer,
)
from smart_agri.core.api.viewsets.base import AuditedModelViewSet, IdempotentCreateMixin
from smart_agri.core.models import CropPlan, DailyLog, Farm, Location, Supervisor, SyncRecord
from smart_agri.core.models.custody import CustodyTransfer
from smart_agri.core.models.sync_conflict import OfflineSyncQuarantine, SyncConflictDLQ
from smart_agri.core.models.task import Task
from smart_agri.core.services.activity_service import ActivityService
from smart_agri.core.services.custody_transfer_service import CustodyTransferService
from smart_agri.core.services.variance import compute_log_variance
from smart_agri.inventory.models import Item


QUARANTINE_LATE_WINDOW = timedelta(hours=24)
BACKEND_OWNED_ACTIVITY_COST_FIELDS = (
    "cost_materials",
    "cost_labor",
    "cost_machinery",
    "cost_overhead",
    "cost_wastage",
    "cost_total",
)

logger = logging.getLogger(__name__)


def _parse_device_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError({"device_timestamp": "صيغة device_timestamp غير صالحة."}) from exc


def _build_success_response(*, payload_uuid, draft_uuid=None, status_value="synced", **extra):
    response = {
        "uuid": payload_uuid,
        "draft_uuid": draft_uuid,
        "status": status_value,
    }
    response.update({key: value for key, value in extra.items() if value is not None})
    return response


def _scrub_backend_owned_activity_fields(payload):
    cleaned = dict(payload or {})
    for field_name in BACKEND_OWNED_ACTIVITY_COST_FIELDS:
        cleaned.pop(field_name, None)
    return cleaned


def _record_dlq(*, farm, actor, conflict_type, conflict_reason, endpoint, http_method, request_payload, idempotency_key, device_timestamp):
    row = SyncConflictDLQ.objects.create(
        farm=farm,
        actor=actor,
        conflict_type=conflict_type,
        conflict_reason=conflict_reason,
        endpoint=endpoint,
        http_method=http_method,
        request_payload=request_payload,
        idempotency_key=idempotency_key,
        device_timestamp=device_timestamp,
    )
    _resolve_superseded_dlq_entries(
        farm=farm,
        actor=actor,
        endpoint=endpoint,
        request_payload=request_payload,
        keep_id=row.id,
    )
    return row


def _extract_replay_identity(payload):
    if not isinstance(payload, dict):
        return None, None
    payload_uuid = payload.get("payload_uuid") or payload.get("uuid")
    draft_uuid = payload.get("draft_uuid")
    return payload_uuid, draft_uuid


def _dlq_matches_replay_identity(row_payload, payload_uuid, draft_uuid):
    if not isinstance(row_payload, dict):
        return False
    row_payload_uuid = row_payload.get("payload_uuid") or row_payload.get("uuid")
    row_draft_uuid = row_payload.get("draft_uuid")
    if payload_uuid and row_payload_uuid == payload_uuid:
        return True
    if draft_uuid and row_draft_uuid == draft_uuid:
        return True
    return False


def _resolve_superseded_dlq_entries(*, farm, actor, endpoint, request_payload, keep_id):
    payload_uuid, draft_uuid = _extract_replay_identity(request_payload)
    if not payload_uuid and not draft_uuid:
        return 0
    now = timezone.now()
    resolved = 0
    qs = SyncConflictDLQ.objects.filter(
        farm=farm,
        actor=actor,
        endpoint=endpoint,
        status="PENDING",
        deleted_at__isnull=True,
    ).exclude(pk=keep_id)
    for row in qs:
        if not _dlq_matches_replay_identity(row.request_payload, payload_uuid, draft_uuid):
            continue
        row.status = "RESOLVED"
        row.resolved_by = actor
        row.resolved_at = now
        row.resolution_notes = (
            f"Superseded by newer replay attempt for payload_uuid={payload_uuid or '-'} "
            f"draft_uuid={draft_uuid or '-'}."
        )
        row.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_notes", "updated_at"])
        resolved += 1
    return resolved


def _mark_replayed_dlq_entries(*, farm, actor, endpoint, payload_uuid=None, draft_uuid=None):
    if not payload_uuid and not draft_uuid:
        return 0
    now = timezone.now()
    resolved = 0
    qs = SyncConflictDLQ.objects.filter(
        farm=farm,
        actor=actor,
        endpoint=endpoint,
        status="PENDING",
        deleted_at__isnull=True,
    )
    for row in qs:
        if not _dlq_matches_replay_identity(row.request_payload, payload_uuid, draft_uuid):
            continue
        row.status = "REPLAYED"
        row.resolved_by = actor
        row.resolved_at = now
        row.resolution_notes = (
            f"Auto-resolved after successful replay for payload_uuid={payload_uuid or '-'} "
            f"draft_uuid={draft_uuid or '-'}."
        )
        row.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_notes", "updated_at"])
        resolved += 1
    return resolved


def _is_truthy_query_param(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _latest_success_response(*, user, category, reference):
    existing_record = (
        SyncRecord.objects.filter(user=user, category=category, reference=reference)
        .order_by("-updated_at")
        .first()
    )
    if existing_record and existing_record.status == SyncRecord.STATUS_SUCCESS:
        payload = existing_record.payload if isinstance(existing_record.payload, dict) else {}
        response_payload = payload.get("response")
        if response_payload:
            return Response(response_payload, status=status.HTTP_200_OK)
    return None


def _enforce_client_sequence(*, user, farm, category, device_id, client_seq, request_path, request_method, request_payload, idempotency_key, device_timestamp, supervisor_id=None):
    max_seq = (
        SyncRecord.objects.filter(
            user=user,
            category=category,
            status=SyncRecord.STATUS_SUCCESS,
            farm=farm,
        )
        .filter(payload__device_id=device_id, payload__supervisor_id=supervisor_id)
        .values_list("payload__client_seq", flat=True)
    )
    max_processed_seq = max((int(value) for value in max_seq if value is not None), default=0)
    if client_seq > max_processed_seq + 1:
        _record_dlq(
            farm=farm,
            actor=user,
            conflict_type="STALE_VERSION",
            conflict_reason=(
                f"Out-of-order replay detected for device={device_id}. "
                f"Expected next seq {max_processed_seq + 1}, got {client_seq}."
            ),
            endpoint=request_path,
            http_method=request_method,
            request_payload=request_payload,
            idempotency_key=idempotency_key,
            device_timestamp=device_timestamp,
        )
        raise ValidationError(
            {
                "client_seq": (
                    f"الترتيب غير صالح. المتوقع {max_processed_seq + 1}، "
                    f"والمرسل {client_seq}."
                ),
                "expected_client_seq": max_processed_seq + 1,
                "retry_allowed": False,
            }
        )


def _save_sync_record(*, user, farm, category, reference, response_payload, log_date=None, extra_payload=None):
    sync_record, _ = SyncRecord.objects.get_or_create(
        user=user,
        category=category,
        reference=reference,
        defaults={"farm": farm},
    )
    sync_record.farm = farm
    sync_record.status = SyncRecord.STATUS_SUCCESS
    payload = dict(extra_payload or {})
    payload["response"] = response_payload
    sync_record.payload = payload
    sync_record.last_error_message = ""
    sync_record.last_attempt_at = timezone.now()
    sync_record.attempt_count = (sync_record.attempt_count or 0) + 1
    sync_record.log_date = log_date
    sync_record.save()
    return sync_record


def _resolve_or_create_daily_log_for_replay(
    *,
    farm,
    supervisor,
    log_date,
    actor,
    parsed_device_timestamp,
    log_payload,
):
    matching_logs = list(
        DailyLog.objects.select_for_update()
        .filter(
            farm=farm,
            log_date=log_date,
            supervisor=supervisor,
            deleted_at__isnull=True,
        )
        .order_by("id")
    )
    if not matching_logs:
        return (
            DailyLog.objects.create(
                farm=farm,
                supervisor=supervisor,
                log_date=log_date,
                created_by=actor,
                updated_by=actor,
                notes=log_payload.get("notes", ""),
                variance_note=log_payload.get("variance_note", ""),
                device_timestamp=parsed_device_timestamp,
            ),
            True,
        )

    keeper = next(
        (log for log in matching_logs if log.activities.filter(deleted_at__isnull=True).exists()),
        matching_logs[0],
    )
    if len(matching_logs) > 1:
        logger.warning(
            "offline_daily_log_replay.duplicate_daily_logs_resolved farm_id=%s supervisor_id=%s log_date=%s keeper_id=%s duplicate_ids=%s",
            farm.id,
            getattr(supervisor, "id", None),
            log_date,
            keeper.id,
            [log.id for log in matching_logs if log.id != keeper.id],
        )

    update_fields = []
    if parsed_device_timestamp and keeper.device_timestamp != parsed_device_timestamp:
        keeper.device_timestamp = parsed_device_timestamp
        update_fields.append("device_timestamp")
    variance_note = log_payload.get("variance_note")
    if variance_note is not None and keeper.variance_note != variance_note:
        keeper.variance_note = variance_note
        update_fields.append("variance_note")
    notes = log_payload.get("notes")
    if notes is not None and keeper.notes != notes:
        keeper.notes = notes
        update_fields.append("notes")
    if update_fields:
        keeper.updated_by = actor
        update_fields.append("updated_by")
        keeper.save(update_fields=update_fields)
    return keeper, False


def _normalize_harvest_payload(payload):
    data = dict(payload or {})
    crop_plan_id = data.get("crop_plan") or data.get("crop_plan_id")
    crop_plan = None
    if crop_plan_id not in (None, ""):
        crop_plan = CropPlan.objects.select_related("farm", "crop").filter(pk=crop_plan_id).first()
        if crop_plan is None:
            raise ValidationError({"crop_plan": "الخطة غير موجودة."})

    farm_id = data.get("farm_id") or data.get("farm") or getattr(crop_plan, "farm_id", None)
    if farm_id in (None, ""):
        raise ValidationError({"farm_id": "farm_id مطلوب."})
    farm = Farm.objects.get(pk=farm_id)

    crop_id = data.get("crop") or data.get("crop_id") or getattr(crop_plan, "crop_id", None)
    if crop_id in (None, ""):
        raise ValidationError({"crop": "crop مطلوب."})

    product_id = data.get("product") or data.get("product_id")
    product_item_id = data.get("product_item")
    if product_id in (None, "") and product_item_id not in (None, "") and crop_plan is not None:
        crop_product = crop_plan.crop.products.filter(item_id=product_item_id).first()
        if crop_product:
            product_id = crop_product.id
    harvest_date = data.get("harvest_date") or data.get("date")
    quantity = data.get("quantity") or data.get("qty")
    if not harvest_date:
        raise ValidationError({"harvest_date": "harvest_date مطلوب."})
    if quantity in (None, ""):
        raise ValidationError({"quantity": "quantity مطلوب."})

    normalized = {
        "farm": farm.id,
        "crop": crop_id,
        "crop_plan": getattr(crop_plan, "id", None),
        "product": product_id,
        "location": data.get("location") or data.get("location_id"),
        "harvest_date": harvest_date,
        "grade": data.get("grade") or "First",
        "quantity": quantity,
        "unit": data.get("unit") or data.get("unit_id"),
        "uom": data.get("uom") or "kg",
    }
    return farm, normalized


class HardenedOfflineDailyLogReplayViewSet(IdempotentCreateMixin, viewsets.ViewSet):
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
        draft_uuid = data.get("draft_uuid")
        lookup_snapshot_version = data.get("lookup_snapshot_version")
        task_contract_snapshot = data.get("task_contract_snapshot")
        device_id = data.get("device_id") or data.get("client_metadata", {}).get("device_id") or f"user-{request.user.id}"
        parsed_device_timestamp = _parse_device_timestamp(data.get("device_timestamp"))
        log_payload = data.get("log") or data.get("logPayload") or {}
        activity_payload = data.get("activity") or data.get("activityPayload") or {}

        if not payload_uuid:
            raise ValidationError({"uuid": "uuid مطلوب للمزامنة الذرية."})
        if not idempotency_key:
            raise ValidationError({"idempotency_key": "idempotency_key مطلوب."})
        if farm_id in (None, ""):
            raise ValidationError({"farm_id": "farm_id مطلوب."})
        if client_seq in (None, ""):
            raise ValidationError({"client_seq": "client_seq مطلوب."})

        replay_response = _latest_success_response(
            user=request.user,
            category="daily_log",
            reference=payload_uuid,
        )
        if replay_response is not None:
            return replay_response

        _ensure_user_has_farm_access(request.user, farm_id)
        farm = Farm.objects.get(pk=farm_id)
        supervisor = None
        if supervisor_id not in (None, ""):
            supervisor = Supervisor.objects.get(pk=supervisor_id, farm=farm)

        try:
            client_seq = int(client_seq)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"client_seq": "client_seq يجب أن يكون رقمًا صحيحًا."}) from exc

        _enforce_client_sequence(
            user=request.user,
            farm=farm,
            category="daily_log",
            device_id=device_id,
            client_seq=client_seq,
            request_path=request.path,
            request_method=request.method,
            request_payload=data,
            idempotency_key=idempotency_key,
            device_timestamp=parsed_device_timestamp,
            supervisor_id=getattr(supervisor, "id", None),
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
                                deleted_at__isnull=True,
                            ).first()
                            if active_plan:
                                plan_locations = list(active_plan.locations.values_list("id", flat=True))
                                if plan_locations:
                                    activity_input["location_ids"] = plan_locations

                activity_input["log"] = daily_log
                activity_input["log_id"] = daily_log.id
                activity_input["idempotency_key"] = idempotency_key
                activity_input["device_timestamp"] = parsed_device_timestamp

                result = ActivityService.maintain_activity(request.user, activity_input, activity_id=None)
                if not result.success or result.data is None:
                    raise ValidationError(result.errors or {"detail": result.message or "تعذر ترحيل النشاط."})

                response_payload = _build_success_response(
                    payload_uuid=payload_uuid,
                    draft_uuid=draft_uuid,
                    log_id=daily_log.id,
                    activity_id=result.data.id,
                    client_seq=client_seq,
                )
                extra_payload = {
                    "device_id": device_id,
                    "client_seq": client_seq,
                    "draft_uuid": draft_uuid,
                    "supervisor_id": getattr(supervisor, "id", None),
                    "lookup_snapshot_version": lookup_snapshot_version,
                    "task_contract_snapshot": task_contract_snapshot,
                }

                variance_snapshot = compute_log_variance(daily_log)
                is_late = bool(parsed_device_timestamp and timezone.now() - parsed_device_timestamp > QUARANTINE_LATE_WINDOW)
                if is_late and variance_snapshot.get("status") == "CRITICAL":
                    quarantine = OfflineSyncQuarantine.objects.create(
                        farm=farm,
                        submitted_by=request.user,
                        variance_type="LATE_CRITICAL_VARIANCE",
                        device_timestamp=parsed_device_timestamp,
                        original_payload=data,
                        idempotency_key=f"{idempotency_key}:quarantine",
                        status="PENDING_REVIEW",
                    )
                    response_payload["status"] = "quarantined"
                    response_payload["quarantine_id"] = quarantine.id
                    extra_payload["quarantine_id"] = quarantine.id
                    extra_payload["variance_status"] = variance_snapshot.get("status")

                _save_sync_record(
                    user=request.user,
                    farm=farm,
                    category="daily_log",
                    reference=payload_uuid,
                    response_payload=response_payload,
                    log_date=daily_log.log_date,
                    extra_payload=extra_payload,
                )
                _mark_replayed_dlq_entries(
                    farm=farm,
                    actor=request.user,
                    endpoint=request.path,
                    payload_uuid=payload_uuid,
                    draft_uuid=draft_uuid,
                )
        except (ValidationError, PermissionDenied, DjangoPermissionDenied) as exc:
            _record_dlq(
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
            _record_dlq(
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

        status_code = status.HTTP_202_ACCEPTED if response_payload.get("status") == "quarantined" else status.HTTP_201_CREATED
        return Response(response_payload, status=status_code)


class OfflineHarvestReplayViewSet(IdempotentCreateMixin, viewsets.ViewSet):
    queryset = SyncRecord.objects.none()
    permission_classes = [permissions.IsAuthenticated]
    enforce_idempotency = True
    model_name = "OfflineHarvestReplay"
    http_method_names = ["post", "head", "options"]

    def create(self, request):
        farm_id = request.data.get("farm_id") if isinstance(request.data, dict) else None
        key, error_response = self._enforce_action_idempotency(request, farm_id=farm_id)
        if error_response:
            return error_response
        response = self._create_impl(request)
        object_id = ""
        if isinstance(getattr(response, "data", None), dict):
            object_id = str(response.data.get("harvest_id") or response.data.get("uuid") or "")
        self._commit_action_idempotency(request, key, object_id=object_id, response=response)
        return response

    def _create_impl(self, request):
        data = request.data or {}
        payload_uuid = data.get("payload_uuid") or data.get("uuid")
        idempotency_key = data.get("idempotency_key")
        client_seq = data.get("client_seq")
        device_id = data.get("device_id") or f"user-{request.user.id}"
        draft_uuid = data.get("draft_uuid")
        parsed_device_timestamp = _parse_device_timestamp(data.get("device_timestamp"))
        payload = data.get("harvest") or data.get("payload") or data

        if not payload_uuid:
            raise ValidationError({"uuid": "uuid مطلوب."})
        if not idempotency_key:
            raise ValidationError({"idempotency_key": "idempotency_key مطلوب."})
        if client_seq in (None, ""):
            raise ValidationError({"client_seq": "client_seq مطلوب."})
        try:
            client_seq = int(client_seq)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"client_seq": "client_seq يجب أن يكون رقمًا صحيحًا."}) from exc

        replay_response = _latest_success_response(user=request.user, category="harvest", reference=payload_uuid)
        if replay_response is not None:
            return replay_response

        farm, normalized_payload = _normalize_harvest_payload(payload)
        _ensure_user_has_farm_access(request.user, farm.id)
        _enforce_client_sequence(
            user=request.user,
            farm=farm,
            category="harvest",
            device_id=device_id,
            client_seq=client_seq,
            request_path=request.path,
            request_method=request.method,
            request_payload=data,
            idempotency_key=idempotency_key,
            device_timestamp=parsed_device_timestamp,
        )

        try:
            serializer = HarvestLotSerializer(data=normalized_payload, context={"request": request})
            serializer.is_valid(raise_exception=True)
            harvest_lot = serializer.save()
        except (ValidationError, PermissionDenied, DjangoPermissionDenied) as exc:
            _record_dlq(
                farm=farm,
                actor=request.user,
                conflict_type="VALIDATION_FAILURE",
                conflict_reason=f"Harvest replay validation failed: {str(exc)}",
                endpoint=request.path,
                http_method=request.method,
                request_payload=data,
                idempotency_key=idempotency_key,
                device_timestamp=parsed_device_timestamp,
            )
            raise
        except (DatabaseError, IntegrityError) as exc:
            _record_dlq(
                farm=farm,
                actor=request.user,
                conflict_type="DATABASE_ERROR",
                conflict_reason=f"Harvest replay database error: {str(exc)}",
                endpoint=request.path,
                http_method=request.method,
                request_payload=data,
                idempotency_key=idempotency_key,
                device_timestamp=parsed_device_timestamp,
            )
            raise

        response_payload = _build_success_response(
            payload_uuid=payload_uuid,
            draft_uuid=draft_uuid,
            status_value="synced",
            harvest_id=harvest_lot.id,
            client_seq=client_seq,
        )
        _save_sync_record(
            user=request.user,
            farm=farm,
            category="harvest",
            reference=payload_uuid,
            response_payload=response_payload,
            log_date=harvest_lot.harvest_date,
            extra_payload={
                "device_id": device_id,
                "client_seq": client_seq,
                "draft_uuid": draft_uuid,
                "payload": normalized_payload,
            },
        )
        return Response(response_payload, status=status.HTTP_201_CREATED)


class OfflineCustodyReplayViewSet(IdempotentCreateMixin, viewsets.ViewSet):
    queryset = SyncRecord.objects.none()
    permission_classes = [permissions.IsAuthenticated]
    enforce_idempotency = True
    model_name = "OfflineCustodyReplay"
    http_method_names = ["post", "head", "options"]

    def create(self, request):
        farm_id = request.data.get("farm_id") if isinstance(request.data, dict) else None
        key, error_response = self._enforce_action_idempotency(request, farm_id=farm_id)
        if error_response:
            return error_response
        response = self._create_impl(request)
        object_id = ""
        if isinstance(getattr(response, "data", None), dict):
            object_id = str(response.data.get("transfer_id") or response.data.get("uuid") or "")
        self._commit_action_idempotency(request, key, object_id=object_id, response=response)
        return response

    def _create_impl(self, request):
        data = request.data or {}
        payload_uuid = data.get("payload_uuid") or data.get("uuid")
        idempotency_key = data.get("idempotency_key")
        client_seq = data.get("client_seq")
        device_id = data.get("device_id") or f"user-{request.user.id}"
        parsed_device_timestamp = _parse_device_timestamp(data.get("device_timestamp"))
        action_name = data.get("action_name") or data.get("action")
        payload = data.get("payload") or {}
        farm_id = data.get("farm_id") or payload.get("farm_id") or payload.get("farm")

        if not payload_uuid:
            raise ValidationError({"uuid": "uuid مطلوب."})
        if not idempotency_key:
            raise ValidationError({"idempotency_key": "idempotency_key مطلوب."})
        if client_seq in (None, ""):
            raise ValidationError({"client_seq": "client_seq مطلوب."})
        if not action_name:
            raise ValidationError({"action_name": "action_name مطلوب."})
        if farm_id in (None, "") and action_name == "issue":
            raise ValidationError({"farm_id": "farm_id مطلوب."})

        try:
            client_seq = int(client_seq)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"client_seq": "client_seq يجب أن يكون رقمًا صحيحًا."}) from exc

        replay_response = _latest_success_response(user=request.user, category="custody", reference=payload_uuid)
        if replay_response is not None:
            return replay_response

        farm = None
        if farm_id not in (None, ""):
            farm = Farm.objects.get(pk=farm_id)
            _ensure_user_has_farm_access(request.user, farm.id)

        _enforce_client_sequence(
            user=request.user,
            farm=farm,
            category="custody",
            device_id=device_id,
            client_seq=client_seq,
            request_path=request.path,
            request_method=request.method,
            request_payload=data,
            idempotency_key=idempotency_key,
            device_timestamp=parsed_device_timestamp,
        )

        try:
            with transaction.atomic():
                if action_name == "issue":
                    serializer = CustodyIssueSerializer(data=payload)
                    serializer.is_valid(raise_exception=True)
                    farm = Farm.objects.get(pk=serializer.validated_data["farm_id"])
                    _ensure_user_has_farm_access(request.user, farm.id)
                    supervisor = Supervisor.objects.get(pk=serializer.validated_data["supervisor_id"], farm=farm)
                    item = Item.objects.get(pk=serializer.validated_data["item_id"])
                    source_location = Location.objects.get(pk=serializer.validated_data["from_location_id"], farm=farm)
                    transfer = CustodyTransferService.issue_transfer(
                        farm=farm,
                        supervisor=supervisor,
                        item=item,
                        source_location=source_location,
                        qty=serializer.validated_data["qty"],
                        actor=request.user,
                        batch_number=serializer.validated_data.get("batch_number") or "",
                        note=serializer.validated_data.get("note") or "",
                        allow_top_up=serializer.validated_data.get("allow_top_up", False),
                        idempotency_key=idempotency_key,
                    )
                else:
                    transfer_id = data.get("transfer_id") or payload.get("transfer_id")
                    if transfer_id in (None, ""):
                        raise ValidationError({"transfer_id": "transfer_id مطلوب."})
                    transfer = CustodyTransfer.objects.select_for_update().get(pk=transfer_id)
                    farm = transfer.farm
                    _ensure_user_has_farm_access(request.user, farm.id)
                    serializer = CustodyTransitionSerializer(data=payload.get("body") or payload)
                    serializer.is_valid(raise_exception=True)
                    if action_name == "accept":
                        transfer = CustodyTransferService.accept_transfer(
                            transfer=transfer,
                            actor=request.user,
                            note=serializer.validated_data.get("note") or "",
                        )
                    elif action_name == "reject":
                        transfer = CustodyTransferService.reject_transfer(
                            transfer=transfer,
                            actor=request.user,
                            note=serializer.validated_data.get("note") or "",
                        )
                    elif action_name == "return":
                        transfer = CustodyTransferService.return_transfer(
                            transfer=transfer,
                            actor=request.user,
                            qty=serializer.validated_data.get("qty"),
                            note=serializer.validated_data.get("note") or "",
                        )
                    else:
                        raise ValidationError({"action_name": "action_name غير مدعوم."})
        except (ValidationError, PermissionDenied, DjangoPermissionDenied) as exc:
            _record_dlq(
                farm=farm,
                actor=request.user,
                conflict_type="VALIDATION_FAILURE",
                conflict_reason=f"Custody replay validation failed: {str(exc)}",
                endpoint=request.path,
                http_method=request.method,
                request_payload=data,
                idempotency_key=idempotency_key,
                device_timestamp=parsed_device_timestamp,
            )
            raise
        except (DatabaseError, IntegrityError) as exc:
            _record_dlq(
                farm=farm,
                actor=request.user,
                conflict_type="DATABASE_ERROR",
                conflict_reason=f"Custody replay database error: {str(exc)}",
                endpoint=request.path,
                http_method=request.method,
                request_payload=data,
                idempotency_key=idempotency_key,
                device_timestamp=parsed_device_timestamp,
            )
            raise

        response_payload = _build_success_response(
            payload_uuid=payload_uuid,
            status_value="synced",
            transfer_id=transfer.id,
            client_seq=client_seq,
            action_name=action_name,
        )
        _save_sync_record(
            user=request.user,
            farm=farm,
            category="custody",
            reference=payload_uuid,
            response_payload=response_payload,
            extra_payload={
                "device_id": device_id,
                "client_seq": client_seq,
                "action_name": action_name,
                "payload": payload,
            },
        )
        return Response(response_payload, status=status.HTTP_201_CREATED)


class SyncConflictDLQViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SyncConflictDLQSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = SyncConflictDLQ.objects.filter(deleted_at__isnull=True).select_related("farm", "actor").order_by("-server_received_at")

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        if user.is_superuser or _user_is_farm_manager(user):
            farm_ids = user_farm_ids(user)
            if farm_ids:
                qs = qs.filter(farm_id__in=farm_ids)
        else:
            qs = qs.filter(actor=user)
        farm_id = self.request.query_params.get("farm_id") or self.request.query_params.get("farm")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        if _is_truthy_query_param(self.request.query_params.get("exclude_demo")):
            qs = qs.exclude(idempotency_key__startswith="demo-").exclude(request_payload__has_key="demo_fixture")
        return qs


class OfflineSyncQuarantineViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OfflineSyncQuarantineSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = OfflineSyncQuarantine.objects.filter(deleted_at__isnull=True).select_related("farm", "submitted_by", "manager_signature").order_by("-server_intercept_time")

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        if user.is_superuser or _user_is_farm_manager(user):
            farm_ids = user_farm_ids(user)
            if farm_ids:
                qs = qs.filter(farm_id__in=farm_ids)
        else:
            qs = qs.filter(submitted_by=user)
        farm_id = self.request.query_params.get("farm_id") or self.request.query_params.get("farm")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        if _is_truthy_query_param(self.request.query_params.get("exclude_demo")):
            qs = qs.exclude(idempotency_key__startswith="demo-").exclude(original_payload__has_key="demo_fixture")
        return qs


class OfflineSyncRecordViewSet(AuditedModelViewSet):
    serializer_class = SyncRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = SyncRecord.objects.select_related("farm").order_by("-updated_at")

    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        if not user.is_superuser and not _user_is_farm_manager(user):
            qs = qs.filter(user=user)
        else:
            qs = _limit_queryset_to_user_farms(qs, user, "farm_id__in")
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        if _is_truthy_query_param(self.request.query_params.get("exclude_demo")):
            qs = qs.exclude(reference__startswith="demo-").exclude(payload__has_key="demo_fixture")
        return qs
