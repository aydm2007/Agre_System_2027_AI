from rest_framework import serializers
from smart_agri.core.constants import StandardUOM
from smart_agri.core.models import (
    CropPlan, CropPlanBudgetLine, PlannedActivity, PlannedMaterial, 
    PlanImportLog, 
    CropTemplate, CropTemplateTask, CropTemplateMaterial,
)


UOM_ALIASES = {
    'liter': StandardUOM.LITER,
    'litre': StandardUOM.LITER,
    'l': StandardUOM.LITER,
    'لتر': StandardUOM.LITER,
    'kg': StandardUOM.KG,
    'كجم': StandardUOM.KG,
    'kilogram': StandardUOM.KG,
    'ton': StandardUOM.TON,
    'طن': StandardUOM.TON,
    'surra': StandardUOM.SURRA,
    'hour': StandardUOM.HOUR,
    'hr': StandardUOM.HOUR,
    'ساعة': StandardUOM.HOUR,
    'lot': StandardUOM.LOT,
    'مقطوعية': StandardUOM.LOT,
    'pcs': StandardUOM.PCS,
    'piece': StandardUOM.PCS,
    'pack': StandardUOM.PACK,
    'unit': StandardUOM.UNIT,
}


def normalize_standard_uom(value):
    if value in (None, ''):
        return value
    normalized = str(value).strip()
    return UOM_ALIASES.get(normalized.lower(), normalized)

class CropPlanSerializer(serializers.ModelSerializer):
    location_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    season = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    locations = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CropPlan
        fields = "__all__"

    def get_locations(self, obj):
        return list(obj.plan_locations.values_list('location_id', flat=True))

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else data.copy() if isinstance(data, dict) else dict(data)

        # 1. Coerce expected_yield null -> 0 (Model doesn't allow null)
        if "expected_yield" in data and data["expected_yield"] is None:
            data["expected_yield"] = 0

        # 2. Resolve or Create season from name/ID
        season_val = data.get("season")
        if season_val and str(season_val).strip():
            from smart_agri.core.models import Season
            from datetime import date
            season_name = str(season_val).strip()
            
            season_obj = None
            if season_name.isdigit():
                season_obj = Season.objects.filter(id=int(season_name)).first()
            
            if not season_obj:
                try:
                    year = int(season_name)
                    if not (1900 <= year <= 3000):
                        year = date.today().year
                except ValueError:
                    year = date.today().year
                
                season_obj, _ = Season.objects.get_or_create(
                    name__iexact=season_name,
                    defaults={
                        "name": season_name,
                        "start_date": date(year, 1, 1),
                        "end_date": date(year, 12, 31),
                        "is_active": True,
                    }
                )
            data["season"] = season_obj.id
        elif "season" in data:
            data["season"] = None

        # 3. Resolve location_ids from names (requires farm context)
        locs_val = data.get("location_ids") or data.get("locations")
        farm_id = data.get("farm")
        if locs_val and isinstance(locs_val, list) and farm_id:
            from smart_agri.core.models import Location
            resolved_ids = []
            for lv in locs_val:
                if isinstance(lv, str) and not str(lv).isdigit():
                    loc_obj = Location.objects.filter(farm_id=farm_id, name__iexact=lv).first()
                    if loc_obj:
                        resolved_ids.append(loc_obj.id)
                elif str(lv).isdigit():
                    resolved_ids.append(int(lv))
            if resolved_ids:
                data["location_ids"] = resolved_ids

        # 4. Resolve crop from name
        crop_val = data.get("crop")
        if crop_val and isinstance(crop_val, str) and not str(crop_val).isdigit():
            from smart_agri.core.models import Crop
            crop_obj = Crop.objects.filter(name__iexact=crop_val).first()
            if crop_obj:
                data["crop"] = crop_obj.id

        return super().to_internal_value(data)

    def create(self, validated_data):
        location_ids = validated_data.pop('location_ids', [])
        plan = super().create(validated_data)
        if location_ids:
            from smart_agri.core.models import CropPlanLocation, Location
            locs = Location.objects.filter(id__in=location_ids, farm=plan.farm)
            plan_locations = [CropPlanLocation(crop_plan=plan, location=loc) for loc in locs]
            CropPlanLocation.objects.bulk_create(plan_locations, ignore_conflicts=True)
        return plan

    def update(self, instance, validated_data):
        location_ids = validated_data.pop('location_ids', None)
        plan = super().update(instance, validated_data)
        if location_ids is not None:
            from smart_agri.core.models import CropPlanLocation, Location
            locs = Location.objects.filter(id__in=location_ids, farm=plan.farm)
            plan.plan_locations.all().delete()
            plan_locations = [CropPlanLocation(crop_plan=plan, location=loc) for loc in locs]
            CropPlanLocation.objects.bulk_create(plan_locations, ignore_conflicts=True)
        return plan

class CropPlanBudgetLineSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source='task.name', read_only=True)

    def to_internal_value(self, data):
        payload = data.copy() if hasattr(data, 'copy') else dict(data)
        if 'uom' in payload:
            payload['uom'] = normalize_standard_uom(payload.get('uom'))
        return super().to_internal_value(payload)

    class Meta:
        model = CropPlanBudgetLine
        fields = "__all__"

class PlannedActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PlannedActivity
        fields = "__all__"

class PlannedMaterialSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_unit_display = serializers.CharField(source='unit.name', read_only=True)
    class Meta:
        model = PlannedMaterial
        fields = "__all__"

class PlanImportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanImportLog
        fields = "__all__"
