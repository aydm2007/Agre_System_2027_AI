from rest_framework import serializers

from smart_agri.core.api.permissions import user_has_sector_finance_authority
from smart_agri.core.models.policy_engine import (
    FarmPolicyBinding,
    PolicyActivationEvent,
    PolicyActivationRequest,
    PolicyExceptionEvent,
    PolicyExceptionRequest,
    PolicyPackage,
    PolicyVersion,
)


def _policy_user_can_manage(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if user.has_perm("finance.can_sector_finance_approve") or user_has_sector_finance_authority(user):
        return True
    return False


def _policy_item_capabilities(*, request, status_value: str | None = None) -> dict:
    can_manage = _policy_user_can_manage(getattr(request, "user", None))
    status_value = str(status_value or "").lower()
    return {
        "can_manage": can_manage,
        "can_edit": can_manage,
        "can_submit": can_manage and status_value == "draft",
        "can_approve": can_manage and status_value in {"draft", "pending"},
        "can_reject": can_manage and status_value not in {"applied", "expired", "retired"},
        "can_apply": can_manage and status_value == "approved",
        "can_retire": can_manage and status_value == "approved",
        "can_simulate": bool(getattr(request, "user", None) and getattr(request.user, "is_authenticated", False) and status_value == "approved"),
    }


class PolicyPackageSerializer(serializers.ModelSerializer):
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = PolicyPackage
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "scope",
            "is_active",
            "capabilities",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_capabilities(self, obj):
        request = self.context.get("request")
        can_manage = _policy_user_can_manage(getattr(request, "user", None))
        return {
            "can_manage": can_manage,
            "can_update": can_manage,
            "can_toggle_active": can_manage,
        }


class PolicyVersionSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source="package.name", read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = PolicyVersion
        fields = [
            "id",
            "package",
            "package_name",
            "version_label",
            "payload",
            "status",
            "capabilities",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["approved_by", "approved_at", "created_at", "updated_at"]

    def get_capabilities(self, obj):
        request = self.context.get("request")
        base = _policy_item_capabilities(request=request, status_value=obj.status)
        return {
            "can_manage": base["can_manage"],
            "can_edit_draft": base["can_manage"] and obj.status == "draft",
            "can_approve": base["can_approve"],
            "can_retire": base["can_retire"],
            "can_simulate": base["can_simulate"],
        }


class FarmPolicyBindingSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source="farm.name", read_only=True)
    policy_package_name = serializers.CharField(source="policy_version.package.name", read_only=True)
    policy_version_label = serializers.CharField(source="policy_version.version_label", read_only=True)

    class Meta:
        model = FarmPolicyBinding
        fields = [
            "id",
            "farm",
            "farm_name",
            "policy_version",
            "policy_package_name",
            "policy_version_label",
            "effective_from",
            "effective_to",
            "is_active",
            "reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PolicyActivationEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = PolicyActivationEvent
        fields = [
            "id",
            "action",
            "actor",
            "actor_username",
            "note",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class PolicyActivationRequestSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source="farm.name", read_only=True)
    policy_package_name = serializers.CharField(source="policy_version.package.name", read_only=True)
    policy_version_label = serializers.CharField(source="policy_version.version_label", read_only=True)
    events = PolicyActivationEventSerializer(many=True, read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = PolicyActivationRequest
        fields = [
            "id",
            "farm",
            "farm_name",
            "policy_version",
            "policy_package_name",
            "policy_version_label",
            "status",
            "rationale",
            "effective_from",
            "simulate_summary",
            "capabilities",
            "requested_by",
            "approved_by",
            "rejected_by",
            "applied_binding",
            "created_at",
            "updated_at",
            "events",
        ]

    def get_capabilities(self, obj):
        request = self.context.get("request")
        base = _policy_item_capabilities(request=request, status_value=obj.status)
        return {
            "can_manage": base["can_manage"],
            "can_submit": base["can_submit"],
            "can_approve": base["can_approve"],
            "can_reject": base["can_reject"],
            "can_apply": base["can_apply"],
        }
        read_only_fields = [
            "status",
            "simulate_summary",
            "requested_by",
            "approved_by",
            "rejected_by",
            "applied_binding",
            "created_at",
            "updated_at",
            "events",
        ]


class PolicyExceptionEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = PolicyExceptionEvent
        fields = [
            "id",
            "action",
            "actor",
            "actor_username",
            "note",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class PolicyExceptionRequestSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source="farm.name", read_only=True)
    events = PolicyExceptionEventSerializer(many=True, read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = PolicyExceptionRequest
        fields = [
            "id",
            "farm",
            "farm_name",
            "status",
            "policy_fields",
            "requested_patch",
            "rationale",
            "effective_from",
            "effective_to",
            "simulate_summary",
            "capabilities",
            "requested_by",
            "approved_by",
            "rejected_by",
            "applied_by",
            "created_at",
            "updated_at",
            "events",
        ]

    def get_capabilities(self, obj):
        request = self.context.get("request")
        base = _policy_item_capabilities(request=request, status_value=obj.status)
        return {
            "can_manage": base["can_manage"],
            "can_submit": base["can_submit"],
            "can_approve": base["can_approve"],
            "can_reject": base["can_reject"],
            "can_apply": base["can_apply"],
        }
        read_only_fields = [
            "status",
            "simulate_summary",
            "requested_by",
            "approved_by",
            "rejected_by",
            "applied_by",
            "created_at",
            "updated_at",
            "events",
        ]
