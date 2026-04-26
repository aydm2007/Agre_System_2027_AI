from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from smart_agri.core.api.permissions import _ensure_user_has_farm_access
from smart_agri.core.services.labor_estimation_service import LaborEstimationService


def _build_hybrid_error_payload(details, message="خطأ في المدخلات"):
    # Keep legacy field-level keys for existing clients/tests, plus structured wrapper.
    payload = {**details}
    payload["error"] = {
        "code": "VALIDATION_ERROR",
        "message": message,
        "details": details,
    }
    return payload


class LaborEstimatePreviewSerializer(serializers.Serializer):
    farm_id = serializers.IntegerField(required=True)
    labor_entry_mode = serializers.ChoiceField(choices=["REGISTERED", "CASUAL_BATCH"], required=True)
    surrah_count = serializers.DecimalField(max_digits=19, decimal_places=4, required=True)
    period_hours = serializers.DecimalField(max_digits=19, decimal_places=4, required=False)
    workers_count = serializers.IntegerField(required=False)
    employee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=False,
    )

    def validate(self, attrs):
        mode = attrs.get("labor_entry_mode")
        if mode == "CASUAL_BATCH" and attrs.get("workers_count") is None:
            raise ValidationError({"workers_count": "هذا الحقل مطلوب في نمط العمالة اليومية."})
        if mode == "REGISTERED" and not attrs.get("employee_ids"):
            raise ValidationError({"employee_ids": "هذا الحقل مطلوب في نمط العمالة المسجلة."})
        return attrs


class LaborEstimateViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request):
        serializer = LaborEstimatePreviewSerializer(data=request.data)
        if not serializer.is_valid():
            # Backward-compatible contract for field-level UI validation in Daily Log.
            details = dict(serializer.errors)
            return Response(
                _build_hybrid_error_payload(details, message="خطأ في المدخلات"),
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = serializer.validated_data

        farm_id = payload["farm_id"]
        _ensure_user_has_farm_access(request.user, farm_id)

        try:
            if payload["labor_entry_mode"] == "CASUAL_BATCH":
                result = LaborEstimationService.preview_for_casual(
                    farm_id=farm_id,
                    surrah_count=payload["surrah_count"],
                    workers_count=payload["workers_count"],
                    period_hours=payload.get("period_hours"),
                )
            else:
                result = LaborEstimationService.preview_for_registered(
                    farm_id=farm_id,
                    surrah_count=payload["surrah_count"],
                    employee_ids=payload["employee_ids"],
                    period_hours=payload.get("period_hours"),
                )
        except DjangoValidationError as exc:
            details = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            message = next(iter(details.values()))[0] if details else "خطأ في المدخلات"
            return Response(
                _build_hybrid_error_payload(details, message=message),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)
