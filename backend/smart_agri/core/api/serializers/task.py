"""
Task Serializer
"""
from rest_framework import serializers
from smart_agri.core.models import Task


class TaskSerializer(serializers.ModelSerializer):
    CARD_ORDER = (
        "execution",
        "materials",
        "labor",
        "well",
        "machinery",
        "fuel",
        "perennial",
        "harvest",
        "control",
        "variance",
        "financial_trace",
    )
    MANDATORY_CARDS = {"execution", "control", "variance"}
    effective_task_contract = serializers.SerializerMethodField(read_only=True)

    def get_effective_task_contract(self, obj):
        return obj.get_effective_contract()

    class Meta:
        model = Task
        fields = "__all__"

    @staticmethod
    def _card_enabled(config):
        if isinstance(config, dict):
            return bool(config.get("enabled"))
        return bool(config)

    def _validate_task_contract(self, task_contract):
        if not isinstance(task_contract, dict):
            raise serializers.ValidationError({"task_contract": "Task contract must be an object."})

        smart_cards = task_contract.get("smart_cards")
        if smart_cards is None:
            return {}
        if not isinstance(smart_cards, dict):
            raise serializers.ValidationError({"task_contract": "Task contract smart_cards must be an object."})

        invalid_cards = sorted(set(smart_cards.keys()) - set(self.CARD_ORDER))
        if invalid_cards:
            raise serializers.ValidationError(
                {"task_contract": f"Unsupported smart cards: {', '.join(invalid_cards)}"}
            )

        enabled_map = {card: self._card_enabled(config) for card, config in smart_cards.items()}
        missing_mandatory = sorted(card for card in self.MANDATORY_CARDS if enabled_map.get(card) is False)
        if missing_mandatory:
            raise serializers.ValidationError(
                {"task_contract": f"Mandatory smart cards cannot be disabled: {', '.join(missing_mandatory)}"}
            )
        return enabled_map

    def validate(self, attrs):
        attrs = super().validate(attrs)
        archetype = attrs.get("archetype", getattr(self.instance, "archetype", Task.Archetype.GENERAL))
        task_contract = attrs.get("task_contract")
        enabled_cards = self._validate_task_contract(task_contract) if task_contract is not None else {}
        if archetype == Task.Archetype.IRRIGATION:
            attrs["requires_well"] = True
        if archetype in {Task.Archetype.MACHINERY, Task.Archetype.FUEL_SENSITIVE}:
            attrs["requires_machinery"] = True
        if archetype in {
            Task.Archetype.PERENNIAL_SERVICE,
            Task.Archetype.BIOLOGICAL_ADJUSTMENT,
        }:
            attrs["requires_tree_count"] = True
            attrs["is_perennial_procedure"] = True
        if archetype == Task.Archetype.HARVEST:
            attrs["is_harvest_task"] = True
        if enabled_cards.get("well"):
            attrs["requires_well"] = True
        if enabled_cards.get("machinery") or enabled_cards.get("fuel"):
            attrs["requires_machinery"] = True
        if enabled_cards.get("perennial"):
            attrs["requires_tree_count"] = True
            attrs["is_perennial_procedure"] = True
        if enabled_cards.get("harvest"):
            attrs["is_harvest_task"] = True
        return attrs
