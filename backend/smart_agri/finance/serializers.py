from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from smart_agri.finance.models_treasury import CashBox, TreasuryTransaction


class CashBoxSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashBox
        fields = [
            "id",
            "farm",
            "name",
            "box_type",
            "currency",
            "balance",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TreasuryTransactionSerializer(serializers.ModelSerializer):
    """Append-only treasury transaction.

    Idempotency is enforced via `X-Idempotency-Key` header.
    The model's `idempotency_key` is server-injected from that header.

    For party/entity analytical dimensions, callers may either provide:
    - `party_content_type` + `party_object_id` (advanced clients)
    - OR `party_model` + `party_id` (human-friendly shorthand)
    """

    party_app_label = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
        help_text="Optional Django app_label when party model name is ambiguous.",
    )
    party_model = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
        help_text="Shorthand for party model name (e.g. employee, customer).",
    )
    party_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = TreasuryTransaction
        fields = [
            "id",
            "farm",
            "cash_box",
            "transaction_type",
            "amount",
            "exchange_rate",
            "reference",
            "note",
            "idempotency_key",
            "party_content_type",
            "party_object_id",
            "party_app_label",
            "party_model",
            "party_id",
            "created_at",
        ]
        read_only_fields = ["id", "farm", "idempotency_key", "created_at"]

    def validate_amount(self, value):
        if value <= Decimal("0.0000"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_exchange_rate(self, value):
        if value <= Decimal("0.0000"):
            raise serializers.ValidationError("Exchange rate must be greater than zero.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # If the advanced fields are provided, keep them.
        if attrs.get("party_content_type") and attrs.get("party_object_id"):
            return attrs

        party_app_label = (attrs.pop("party_app_label", None) or "").strip() or None
        party_model = (attrs.pop("party_model", None) or "").strip().lower() or None
        party_id = (attrs.pop("party_id", None) or "").strip() or None

        if party_model and not party_id:
            raise serializers.ValidationError({"party_id": "party_id is required when party_model is provided."})
        if party_id and not party_model:
            raise serializers.ValidationError({"party_model": "party_model is required when party_id is provided."})

        if party_model and party_id:
            if party_app_label:
                attrs["party_content_type"] = ContentType.objects.get(app_label=party_app_label, model=party_model)
            else:
                matches = ContentType.objects.filter(model=party_model)
                if matches.count() != 1:
                    raise serializers.ValidationError(
                        {
                            "party_model": "Ambiguous party model. Provide party_app_label or use party_content_type/party_object_id.",
                        }
                    )
                attrs["party_content_type"] = matches.first()
            attrs["party_object_id"] = str(party_id)

        return attrs
