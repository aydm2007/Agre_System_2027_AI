from rest_framework import serializers

from smart_agri.core.models import CustodyTransfer


class CustodyTransferSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    supervisor_name = serializers.CharField(source="supervisor.name", read_only=True)
    source_location_name = serializers.CharField(source="source_location.name", read_only=True)
    custody_location_name = serializers.CharField(source="custody_location.name", read_only=True)

    class Meta:
        model = CustodyTransfer
        fields = [
            "id",
            "farm",
            "supervisor",
            "supervisor_name",
            "item",
            "item_name",
            "source_location",
            "source_location_name",
            "custody_location",
            "custody_location_name",
            "status",
            "issued_qty",
            "accepted_qty",
            "returned_qty",
            "outstanding_qty",
            "batch_number",
            "note",
            "issued_at",
            "accepted_at",
            "rejected_at",
            "reconciled_at",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CustodyIssueSerializer(serializers.Serializer):
    farm_id = serializers.IntegerField()
    supervisor_id = serializers.IntegerField()
    item_id = serializers.IntegerField()
    from_location_id = serializers.IntegerField()
    qty = serializers.CharField()
    batch_number = serializers.CharField(required=False, allow_blank=True, default="")
    note = serializers.CharField(required=False, allow_blank=True, default="")
    allow_top_up = serializers.BooleanField(required=False, default=False)


class CustodyTransitionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
    qty = serializers.CharField(required=False, allow_blank=True, allow_null=True)
