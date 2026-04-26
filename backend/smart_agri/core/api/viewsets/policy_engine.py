from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from smart_agri.core.api.error_contract import build_error_payload
from smart_agri.core.api.permissions import _ensure_user_has_farm_access, _limit_queryset_to_user_farms
from smart_agri.core.api.serializers import (
    FarmPolicyBindingSerializer,
    PolicyActivationRequestSerializer,
    PolicyExceptionRequestSerializer,
    PolicyPackageSerializer,
    PolicyVersionSerializer,
)
from smart_agri.core.api.viewsets.base import AuditedModelViewSet
from smart_agri.core.models import (
    Farm,
    FarmPolicyBinding,
    PolicyActivationRequest,
    PolicyExceptionRequest,
    PolicyPackage,
    PolicyVersion,
)
from smart_agri.core.services.policy_engine_service import PolicyEngineService


def _resolve_farm_from_request(*, request):
    farm_id = request.query_params.get("farm") or request.data.get("farm")
    if not farm_id:
        return None, Response(
            build_error_payload("Farm id is required.", request=request, code="POLICY_FARM_REQUIRED"),
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        farm_id = int(farm_id)
    except (TypeError, ValueError):
        return None, Response(
            build_error_payload("Invalid farm id.", request=request, code="INVALID_FARM_ID"),
            status=status.HTTP_400_BAD_REQUEST,
        )
    farm = Farm.objects.filter(pk=farm_id, deleted_at__isnull=True).first()
    if farm is None:
        return None, Response(
            build_error_payload("Farm not found.", request=request, code="FARM_NOT_FOUND"),
            status=status.HTTP_404_NOT_FOUND,
        )
    if request.user and request.user.is_authenticated:
        _ensure_user_has_farm_access(request.user, farm.id)
    return farm, None


class PolicyPackageViewSet(AuditedModelViewSet):
    queryset = PolicyPackage.objects.all()
    serializer_class = PolicyPackageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(is_active=True)
        return qs.order_by("name")

    def perform_create(self, serializer):
        instance = PolicyEngineService.create_package(actor=self.request.user, **serializer.validated_data)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = PolicyEngineService.update_package(
            actor=self.request.user,
            instance=serializer.instance,
            **serializer.validated_data,
        )
        serializer.instance = instance

    @action(detail=False, methods=["get"], url_path="usage-snapshot")
    def usage_snapshot(self, request):
        return Response(PolicyEngineService.package_usage_snapshot())


class PolicyVersionViewSet(AuditedModelViewSet):
    queryset = PolicyVersion.objects.select_related("package").all()
    serializer_class = PolicyVersionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        package_id = self.request.query_params.get("package")
        status_filter = self.request.query_params.get("status")
        if package_id:
            qs = qs.filter(package_id=package_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by("package__name", "-created_at")

    def perform_create(self, serializer):
        instance = PolicyEngineService.create_version(
            actor=self.request.user,
            package=serializer.validated_data["package"],
            version_label=serializer.validated_data["version_label"],
            payload=serializer.validated_data.get("payload") or {},
        )
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = PolicyEngineService.update_version(
            actor=self.request.user,
            instance=serializer.instance,
            **serializer.validated_data,
        )
        serializer.instance = instance

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request)
        if error_response is not None:
            return error_response
        instance = PolicyEngineService.approve_version(actor=request.user, instance=instance)
        serializer = self.get_serializer(instance)
        response = Response(serializer.data)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request)
        if error_response is not None:
            return error_response
        instance = PolicyEngineService.retire_version(actor=request.user, instance=instance)
        serializer = self.get_serializer(instance)
        response = Response(serializer.data)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response

    @action(detail=True, methods=["get"], url_path="simulate")
    def simulate(self, request, pk=None):
        instance = self.get_object()
        farm, error_response = _resolve_farm_from_request(request=request)
        if error_response is not None:
            return error_response
        payload = PolicyEngineService.activation_eligibility(farm=farm, policy_version=instance)
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="activation-eligibility")
    def activation_eligibility(self, request, pk=None):
        return self.simulate(request, pk=pk)

    @action(detail=True, methods=["post"], url_path="diff")
    def diff(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request)
        if error_response is not None:
            return error_response
        compare_to_version_id = request.data.get("compare_to_version")
        farm = None
        compare_to_version = None
        if compare_to_version_id:
            compare_to_version = PolicyVersion.objects.filter(pk=compare_to_version_id).first()
            if compare_to_version is None:
                return Response(
                    build_error_payload("Comparison policy version not found.", request=request, code="POLICY_VERSION_NOT_FOUND"),
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            farm, error_response = _resolve_farm_from_request(request=request)
            if error_response is not None:
                return error_response
        payload = PolicyEngineService.diff_policy_version(
            policy_version=instance,
            compare_to_version=compare_to_version,
            farm=farm,
        )
        response = Response(payload, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response


class FarmPolicyBindingViewSet(AuditedModelViewSet):
    queryset = FarmPolicyBinding.objects.select_related("farm", "policy_version", "policy_version__package").all()
    serializer_class = FarmPolicyBindingSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        farm_id = self.request.query_params.get("farm")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        if self.request.user.is_superuser:
            return qs.order_by("-effective_from")
        return _limit_queryset_to_user_farms(qs, self.request.user, "farm_id__in").order_by("-effective_from")


class PolicyActivationRequestViewSet(AuditedModelViewSet):
    queryset = PolicyActivationRequest.objects.select_related(
        "farm",
        "policy_version",
        "policy_version__package",
        "requested_by",
        "approved_by",
        "rejected_by",
        "applied_binding",
    ).prefetch_related("events")
    serializer_class = PolicyActivationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        farm_id = self.request.query_params.get("farm")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        if self.request.user.is_superuser:
            return qs.order_by("-created_at")
        return _limit_queryset_to_user_farms(qs, self.request.user, "farm_id__in").order_by("-created_at")

    def perform_create(self, serializer):
        instance = PolicyEngineService.create_activation_request(
            actor=self.request.user,
            farm=serializer.validated_data["farm"],
            policy_version=serializer.validated_data["policy_version"],
            rationale=serializer.validated_data.get("rationale", ""),
            effective_from=serializer.validated_data.get("effective_from"),
        )
        serializer.instance = instance

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request, farm_id=instance.farm_id)
        if error_response is not None:
            return error_response
        instance = PolicyEngineService.submit_activation_request(actor=request.user, instance=instance)
        serializer = self.get_serializer(instance)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request, farm_id=instance.farm_id)
        if error_response is not None:
            return error_response
        instance = PolicyEngineService.approve_activation_request(actor=request.user, instance=instance)
        serializer = self.get_serializer(instance)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request, farm_id=instance.farm_id)
        if error_response is not None:
            return error_response
        instance = PolicyEngineService.reject_activation_request(
            actor=request.user,
            instance=instance,
            note=request.data.get("note", ""),
        )
        serializer = self.get_serializer(instance)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request, farm_id=instance.farm_id)
        if error_response is not None:
            return error_response
        instance = PolicyEngineService.apply_activation_request(actor=request.user, instance=instance)
        serializer = self.get_serializer(instance)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response

    @action(detail=False, methods=["get"], url_path="timeline-snapshot")
    def timeline_snapshot(self, request):
        return Response(PolicyEngineService.activation_timeline_snapshot())


class PolicyExceptionRequestViewSet(AuditedModelViewSet):
    queryset = PolicyExceptionRequest.objects.select_related(
        "farm",
        "requested_by",
        "approved_by",
        "rejected_by",
        "applied_by",
    ).prefetch_related("events")
    serializer_class = PolicyExceptionRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        farm_id = self.request.query_params.get("farm")
        if farm_id:
            qs = qs.filter(farm_id=farm_id)
        if self.request.user.is_superuser:
            return qs.order_by("-created_at")
        return _limit_queryset_to_user_farms(qs, self.request.user, "farm_id__in").order_by("-created_at")

    def perform_create(self, serializer):
        instance = PolicyEngineService.create_exception_request(
            actor=self.request.user,
            farm=serializer.validated_data["farm"],
            requested_patch=serializer.validated_data.get("requested_patch") or {},
            rationale=serializer.validated_data.get("rationale", ""),
            effective_from=serializer.validated_data.get("effective_from"),
            effective_to=serializer.validated_data.get("effective_to"),
        )
        serializer.instance = instance

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request, farm_id=instance.farm_id)
        if error_response is not None:
            return error_response
        instance = PolicyEngineService.submit_exception_request(actor=request.user, instance=instance)
        serializer = self.get_serializer(instance)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request, farm_id=instance.farm_id)
        if error_response is not None:
            return error_response
        instance = PolicyEngineService.approve_exception_request(actor=request.user, instance=instance)
        serializer = self.get_serializer(instance)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request, farm_id=instance.farm_id)
        if error_response is not None:
            return error_response
        instance = PolicyEngineService.reject_exception_request(
            actor=request.user,
            instance=instance,
            note=request.data.get("note", ""),
        )
        serializer = self.get_serializer(instance)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        instance = self.get_object()
        key, error_response = self._enforce_action_idempotency(request, farm_id=instance.farm_id)
        if error_response is not None:
            return error_response
        instance = PolicyEngineService.apply_exception_request(actor=request.user, instance=instance)
        serializer = self.get_serializer(instance)
        response = Response(serializer.data, status=status.HTTP_200_OK)
        self._commit_action_idempotency(request, key, object_id=str(instance.id), response=response)
        return response

    @action(detail=False, methods=["get"], url_path="pressure-snapshot")
    def pressure_snapshot(self, request):
        return Response(PolicyEngineService.exception_pressure_snapshot())
