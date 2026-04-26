from django.db import transaction

from smart_agri.core.api.permissions import _ensure_user_has_farm_access
from smart_agri.finance.models import CostCenter


class CostCenterService:
    """Service-layer mutations for analytical cost center master data."""

    @staticmethod
    @transaction.atomic
    def create_cost_center(*, user, **validated_data) -> CostCenter:
        farm = validated_data.get("farm")
        if farm:
            _ensure_user_has_farm_access(user, farm.id)
        instance = CostCenter(**validated_data)
        instance.full_clean()
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def update_cost_center(*, user, instance: CostCenter, **validated_data) -> CostCenter:
        _ensure_user_has_farm_access(user, instance.farm_id)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.full_clean()
        instance.save()
        return instance
