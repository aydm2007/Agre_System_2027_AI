"""
Farm Serializer Module
"""
from decimal import Decimal

from django.db import OperationalError, ProgrammingError
from rest_framework import serializers
from django.utils.text import slugify
from typing import Optional

from smart_agri.core.models import Farm, FarmCrop, LocationIrrigationPolicy, Location
from smart_agri.core.api.permissions import user_has_sector_finance_authority


class FarmSerializer(serializers.ModelSerializer):
    farm_crops = serializers.SerializerMethodField()
    area = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Total farm area (optional).",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Free-form notes about the farm.",
    )
    sales_tax_percentage = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = [
            "id",
            "name",
            "slug",
            "region",
            "area",
            "description",
            "sales_tax_percentage",
            "settings",
            "farm_crops",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at"]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def get_farm_crops(self, obj):
        links = (
            FarmCrop.objects.filter(farm=obj, deleted_at__isnull=True)
            .select_related("crop")
            .values("id", "crop_id", "crop__name")
        )
        return [
            {"id": link["id"], "crop": link["crop_id"], "crop_name": link["crop__name"]}
            for link in links
        ]

    def get_sales_tax_percentage(self, obj):
        try:
            settings = getattr(obj, "settings", None)
        except (AttributeError, Farm.settings.RelatedObjectDoesNotExist):
            return Decimal("0.00")
        except (ProgrammingError, OperationalError):
            # Schema verification should catch drift, but the API must not crash the dashboard.
            return Decimal("0.00")

        if not settings:
            return Decimal("0.00")

        value = getattr(settings, "sales_tax_percentage", None)
        return value if value is not None else Decimal("0.00")

    def get_settings(self, obj):
        try:
            settings = getattr(obj, "settings", None)
            if settings:
                return settings.policy_snapshot()
        except (AttributeError, Farm.settings.RelatedObjectDoesNotExist, OperationalError, ProgrammingError):
            pass
        return {}

    def to_internal_value(self, data):
        mutable = data.copy()
        for key in ("area", "description"):
            if key in mutable and mutable[key] == "":
                mutable[key] = None
        return super().to_internal_value(mutable)

    def _generate_unique_slug(self, base_slug: str, instance: Optional[Farm] = None) -> str:
        base = slugify(base_slug or "") or "farm"
        candidate = base
        queryset = Farm.objects.all()
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        suffix = 2
        while queryset.filter(slug=candidate).exists():
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        name = attrs.get("name") or (instance.name if instance else None)
        slug_value = attrs.get("slug") or (instance.slug if instance else None)
        if name:
            base_slug = slug_value or name
            attrs["slug"] = self._generate_unique_slug(base_slug, instance)
        return attrs


class LocationWellSerializer(serializers.ModelSerializer):
    """
    [Agri-Guardian] Serializer for LocationWell linking.
    Accepts location_id and asset_id for write operations (Frontend Contract).
    """
    from smart_agri.core.models import LocationWell, Location, Asset
    
    # Read-only display fields
    location_name = serializers.CharField(source='location.name', read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    asset_code = serializers.CharField(source='asset.code', read_only=True)
    
    # Write-only ID fields (Frontend sends these)
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        source='location',
        write_only=True,
        required=False
    )
    asset_id = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects.filter(category='Well'),
        source='asset',
        write_only=True,
        required=False
    )
    depth_meters = serializers.DecimalField(
        source='well_depth',
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    discharge_rate_lps = serializers.DecimalField(
        source='capacity_lps',
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
    )

    class Meta:
        from smart_agri.core.models import LocationWell
        model = LocationWell
        fields = [
            'id', 
            'location', 'location_id', 'location_name',
            'asset', 'asset_id', 'asset_name', 'asset_code',
            'well_depth', 'depth_meters', 'pump_type', 'capacity_lps', 'discharge_rate_lps',
            'status', 'is_operational', 'last_serviced_at', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'location', 'asset', 'created_at', 'updated_at']


class LocationIrrigationPolicySerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source="location.name", read_only=True)
    farm_id = serializers.IntegerField(source="location.farm_id", read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        source="location",
        write_only=True,
        required=False,
    )

    class Meta:
        model = LocationIrrigationPolicy
        fields = [
            "id",
            "location",
            "location_id",
            "location_name",
            "farm_id",
            "zakat_rule",
            "valid_daterange",
            "approved_by",
            "approved_at",
            "reason",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
            "location",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if request and request.method in ("POST", "PUT", "PATCH"):
            if not user_has_sector_finance_authority(user):
                raise serializers.ValidationError("Only sector finance authority can manage irrigation policies.")
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        validated_data["approved_by"] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        validated_data["approved_by"] = user
        return super().update(instance, validated_data)
