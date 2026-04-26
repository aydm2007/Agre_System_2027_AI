"""
Tree Serializers
"""
from decimal import Decimal, ROUND_HALF_UP
from rest_framework import serializers
from smart_agri.core.models import (
    TreeProductivityStatus, TreeLossReason, 
    LocationTreeStock, TreeStockEvent, CropVariety,
    TreeServiceCoverage, Location
)
from .location import LocationSerializer
from .crop import CropVarietySerializer


class TreeProductivityStatusSerializer(serializers.ModelSerializer):
    @staticmethod
    def _normalize_mojibake(value):
        if not isinstance(value, str) or not value:
            return value
        if "Ø" not in value and "Ù" not in value:
            return value
        try:
            repaired = value.encode("latin-1").decode("utf-8")
            # Return repaired only if it now contains Arabic codepoints.
            if any("\u0600" <= ch <= "\u06FF" for ch in repaired):
                return repaired
        except (ValidationError, ValueError, TypeError):
            return value
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["name_ar"] = self._normalize_mojibake(data.get("name_ar"))
        return data

    class Meta:
        model = TreeProductivityStatus
        fields = ["id", "code", "name_en", "name_ar", "description"]


class TreeLossReasonSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        name_ar = data.get("name_ar")
        if isinstance(name_ar, str) and ("Ø" in name_ar or "Ù" in name_ar):
            try:
                repaired = name_ar.encode("latin-1").decode("utf-8")
                if any("\u0600" <= ch <= "\u06FF" for ch in repaired):
                    data["name_ar"] = repaired
            except (ValidationError, ValueError, TypeError) as e:
                import logging
                logging.getLogger(__name__).warning("TreeLossReason encoding fix failed: %s", e)
        return data

    class Meta:
        model = TreeLossReason
        fields = ["id", "code", "name_en", "name_ar", "description"]


class LocationTreeStockSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    crop_variety = CropVarietySerializer(read_only=True)
    productivity_status = TreeProductivityStatusSerializer(read_only=True)
    service_stats = serializers.SerializerMethodField()

    class Meta:
        model = LocationTreeStock
        fields = [
            'id',
            'location',
            'crop_variety',
            'current_tree_count',
            'productivity_status',
            'planting_date',
            'source',
            'notes',
            'updated_at',
            'created_at',
            'service_stats',
        ]

    def validate_current_tree_count(self, value):
        if value < 0:
            raise serializers.ValidationError("لا يمكن أن يكون مخزون الأشجار بالسالب في مزارع اليمن.")
        return value

    def update(self, instance, validated_data):
        new_stock = validated_data.get('current_tree_count', instance.current_tree_count)
        if new_stock < 0:
            raise serializers.ValidationError("العملية مرفوضة: المخزون الناتج سيكون أقل من الصفر.")
        return super().update(instance, validated_data)

    @staticmethod
    def _empty_breakdown():
        return {
            'general': 0,
            'irrigation': 0,
            'fertilization': 0,
            'pruning': 0,
        }

    @classmethod
    def _empty_stats(cls):
        return {
            'total_serviced': 0,
            'entries': 0,
            'last_service_date': None,
            'last_recorded_at': None,
            'last_activity_id': None,
            'breakdown': cls._empty_breakdown(),
        }

    @staticmethod
    def _serialize_date(value):
        if not value:
            return None
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _serialize_datetime(value):
        if not value:
            return None
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)

    def _format_service_stats(self, stats, current_tree_count):
        base = self._empty_stats()
        payload = {
            'total_serviced': base['total_serviced'],
            'entries': base['entries'],
            'last_service_date': base['last_service_date'],
            'last_recorded_at': base['last_recorded_at'],
            'last_activity_id': base['last_activity_id'],
            'breakdown': base['breakdown'],
        }
        if stats:
            payload['total_serviced'] = int(stats.get('total_serviced') or 0)
            payload['entries'] = int(stats.get('entries') or 0)
            payload['last_service_date'] = stats.get('last_service_date')
            payload['last_recorded_at'] = stats.get('last_recorded_at')
            payload['last_activity_id'] = stats.get('last_activity_id')
            breakdown = stats.get('breakdown') or {}
            payload['breakdown'] = {
                'general': int(breakdown.get('general') or 0),
                'irrigation': int(breakdown.get('irrigation') or 0),
                'fertilization': int(breakdown.get('fertilization') or 0),
                'pruning': int(breakdown.get('pruning') or 0),
            }
        else:
            payload['breakdown'] = self._empty_breakdown()

        current_total = Decimal(str(current_tree_count or 0))
        coverage_ratio = None
        if current_total > 0:
            serviced_total = Decimal(str(payload['total_serviced'] or 0))
            coverage_ratio = (serviced_total / current_total).quantize(
                Decimal("0.0001"),
                rounding=ROUND_HALF_UP,
            )

        payload['coverage_ratio'] = coverage_ratio
        payload['last_service_date'] = self._serialize_date(payload['last_service_date'])
        payload['last_recorded_at'] = self._serialize_datetime(payload['last_recorded_at'])
        return payload

    def get_service_stats(self, obj):
        stats = getattr(obj, '_service_stats', None) or {}
        period_stats = stats.get('period')
        lifetime_stats = stats.get('lifetime')
        latest_entry = stats.get('latest_entry')
        if latest_entry:
            latest_entry = {
                **latest_entry,
                'recorded_at': self._serialize_datetime(latest_entry.get('recorded_at')),
                'activity_date': self._serialize_date(latest_entry.get('activity_date')),
            }
        return {
            'period': self._format_service_stats(period_stats, obj.current_tree_count),
            'lifetime': self._format_service_stats(lifetime_stats, obj.current_tree_count),
            'latest_entry': latest_entry,
        }


class TreeStockEventSerializer(serializers.ModelSerializer):
    location_tree_stock = LocationTreeStockSerializer(read_only=True)
    loss_reason = TreeLossReasonSerializer(read_only=True)
    activity_id = serializers.IntegerField(read_only=True, allow_null=True)
    tree_loss_reason_id = serializers.IntegerField(source='loss_reason_id', read_only=True, allow_null=True)

    class Meta:
        model = TreeStockEvent
        fields = [
            'id',
            'location_tree_stock',
            'activity_id',
            'event_type',
            'event_timestamp',
            'tree_count_delta',
            'resulting_tree_count',
            'loss_reason',
            'tree_loss_reason_id',
            'planting_date',
            'source',
            'harvest_quantity',
            'harvest_uom',
            'water_volume',
            'water_uom',
            'fertilizer_quantity',
            'fertilizer_uom',
            'notes',
        ]


class ManualTreeAdjustmentSerializer(serializers.Serializer):
    stock_id = serializers.PrimaryKeyRelatedField(
        source='stock', queryset=LocationTreeStock.objects.all(), required=False
    )
    location_id = serializers.PrimaryKeyRelatedField(
        source='location', queryset=Location.objects.all(), required=False
    )
    variety_id = serializers.PrimaryKeyRelatedField(
        source='variety', queryset=CropVariety.objects.all(), required=False
    )
    resulting_tree_count = serializers.IntegerField(required=False, min_value=0)
    delta = serializers.IntegerField(required=False)
    reason = serializers.CharField(max_length=250)
    planting_date = serializers.DateField(required=False, allow_null=True)
    source = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=120)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500)

    def validate(self, attrs):
        stock = attrs.get('stock')
        location = attrs.get('location')
        variety = attrs.get('variety')

        if stock is None and (location is None or variety is None):
            raise serializers.ValidationError('يجب اختيار المخزون أو (الموقع والصنف).')

        if stock is not None and location is not None and stock.location_id != location.id:
            raise serializers.ValidationError({'location_id': 'الموقع المختار لا يطابق مخزون الشجرة.'})
        if stock is not None and variety is not None and stock.crop_variety_id != variety.id:
            raise serializers.ValidationError({'variety_id': 'الصنف المختار لا يطابق مخزون الشجرة.'})

        delta = attrs.get('delta')
        resulting = attrs.get('resulting_tree_count')
        if delta is None and resulting is None:
            raise serializers.ValidationError(
                {'resulting_tree_count': 'يجب تحديد الفرق في العدد أو العدد الناتج.'}
            )
        if delta is not None and resulting is not None:
            raise serializers.ValidationError({'delta': 'لا يمكن تحديد الفرق والعدد الناتج معاً.'})

        return attrs


class TreeProductivityRefreshSerializer(serializers.Serializer):
    stock_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, allow_empty=False
    )
    farm_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, allow_empty=False
    )
    batch_size = serializers.IntegerField(required=False, min_value=1, max_value=2000)
    as_of = serializers.DateField(required=False)


class ActivityTreeServiceCoverageSerializer(serializers.ModelSerializer):
    location_id = serializers.IntegerField(source="location.id", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    variety_id = serializers.IntegerField(source="crop_variety.id", read_only=True)
    variety_name = serializers.CharField(source="crop_variety.name", read_only=True)
    recorded_by_id = serializers.IntegerField(source='recorded_by.id', read_only=True)
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TreeServiceCoverage
        fields = [
              "id",
              "location_id",
              "location_name",
              "variety_id",
              "variety_name",
              "service_count",
              "service_type",
              "service_scope",
              "distribution_mode",
              "distribution_factor",
              "total_before",
              "total_after",
              "notes",
            "recorded_by_id",
            "recorded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_recorded_by_name(self, obj):
        user = getattr(obj, 'recorded_by', None)
        if not user:
            return None
        if hasattr(user, 'get_full_name'):
            full_name = user.get_full_name()
            if full_name:
                return full_name
        return getattr(user, 'username', None)


class ActivityTreeServiceCoverageInputSerializer(serializers.Serializer):
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=Location.objects.filter(deleted_at__isnull=True),
        required=False,
        allow_null=True,
    )
    variety_id = serializers.PrimaryKeyRelatedField(
        source='crop_variety',
        queryset=CropVariety.objects.all(),
        required=True,
    )
    service_count = serializers.IntegerField(min_value=0)
    service_type = serializers.ChoiceField(
        choices=TreeServiceCoverage.SERVICE_TYPE_CHOICES,
        required=False,
        default=TreeServiceCoverage.GENERAL,
    )
    service_scope = serializers.CharField(
        required=False,
        allow_null=True,
        default=None,
    )
    distribution_mode = serializers.ChoiceField(
        choices=TreeServiceCoverage.DISTRIBUTION_MODE_CHOICES,
        required=False,
        default=TreeServiceCoverage.DISTRIBUTION_UNIFORM,
    )
    distribution_factor = serializers.DecimalField(
        max_digits=10,
        decimal_places=4,
        required=False,
        allow_null=True,
        min_value=Decimal("0"),
    )
    total_before = serializers.IntegerField(required=False, allow_null=True)
    total_after = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        service_count = attrs.get("service_count")
        if service_count is None or service_count < 0:
            raise serializers.ValidationError({"service_count": "عدد مرات الخدمة لا يمكن أن يكون سالباً."})

        # Round 22: Service Scope Normalization (Mapping Legacy Backend -> Modern Schema)
        # If the frontend/old-code sends 'general' as a scope, it's actually a service_type.
        scope_val = attrs.get("service_scope")
        type_val = attrs.get("service_type")
        
        valid_scopes = {'farm', 'location', 'tree'}
        valid_types = {t[0] for t in TreeServiceCoverage.SERVICE_TYPE_CHOICES}

        if scope_val and scope_val not in valid_scopes:
            if scope_val in valid_types:
                # Use it as type if type is default/missing
                if not type_val or type_val == TreeServiceCoverage.GENERAL:
                    attrs['service_type'] = scope_val
            # Reset scope to a valid default
            attrs['service_scope'] = 'location'

        return attrs
