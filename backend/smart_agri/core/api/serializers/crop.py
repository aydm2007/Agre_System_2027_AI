"""
Crop Serializers
"""
import logging
from decimal import Decimal
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.db.models import Q

from smart_agri.core.models import (
    Crop, CropProduct, CropProductUnit, CropMaterial, 
    CropTemplate, CropTemplateMaterial, CropTemplateTask, 
    CropVariety, FarmCrop, Item, Farm, Unit, Task,
    CropRecipe, CropRecipeMaterial, CropRecipeTask
)
from smart_agri.core.api.permissions import (
    user_farm_ids, 
    _ensure_user_has_farm_access
)
from .unit import UnitSerializer

logger = logging.getLogger(__name__)


class CropProductUnitSerializer(serializers.ModelSerializer):
    unit_detail = UnitSerializer(source='unit', read_only=True)

    class Meta:
        model = CropProductUnit
        fields = [
            'id',
            'unit',
            'unit_detail',
            'uom',
            'multiplier',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'unit_detail', 'created_at', 'updated_at']

    def validate_multiplier(self, value):
        if value is None or value <= 0:
            raise ValidationError('معامل التحويل يجب أن يكون أكبر من صفر.')
        return value


class CropProductSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    farm_name = serializers.SerializerMethodField()
    item = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.filter(deleted_at__isnull=True),
        allow_null=False,
        required=True,
    )
    name = serializers.CharField(required=False, allow_blank=True)  # [Agri-Guardian] Auto-filled from Item if missing
    farm = serializers.PrimaryKeyRelatedField(
        queryset=Farm.objects.filter(deleted_at__isnull=True),
        allow_null=False,
        required=True,
    )

    def get_farm_name(self, obj):
        return obj.farm.name if obj.farm else None
    units = CropProductUnitSerializer(source='unit_options', many=True, required=False)

    class Meta:
        model = CropProduct
        fields = [
            "id",
            "farm",
            "farm_name",
            "crop",
            "crop_name",
            "item",
            "name",
            "is_primary",
            "notes",
            "quality_grade",
            "packing_type",
            "reference_price",
            "pack_size",
            "pack_uom",
            "units",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "crop_name",
            "farm_name",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        crop = attrs.get("crop") or getattr(self.instance, "crop", None)
        has_explicit_farm = "farm" in attrs or self.instance is None
        farm = attrs.get("farm") if "farm" in attrs else getattr(self.instance, "farm", None)
        
        # [Agri-Guardian] Auto-Name from Item if missing (Frontend Convenience)
        if 'name' not in attrs or not attrs['name']:
            item = attrs.get('item') or getattr(self.instance, 'item', None)
            if item:
                attrs['name'] = item.name

        if crop is None:
            raise ValidationError({"detail": "محصول غير موجود."})
            

            
        if farm is not None:
            attrs["farm"] = farm
            
        request = self.context.get("request")
        if request is not None:
            self._ensure_crop_access(request.user, crop)
            if farm is not None:
                _ensure_user_has_farm_access(request.user, getattr(farm, "id", None))
        if farm is not None and not FarmCrop.objects.filter(
            farm_id=getattr(farm, "id", None),
            crop_id=getattr(crop, "id", None),
            deleted_at__isnull=True,
        ).exists():
            raise ValidationError({"farm": "المحصول غير مرتبط بهذه المزرعة."})
        return attrs

    def create(self, validated_data):
        units_data = validated_data.pop('unit_options', [])
        product = super().create(validated_data)
        self._sync_units(product, units_data)
        return product

    def update(self, instance, validated_data):
        units_data = validated_data.pop('unit_options', None)
        product = super().update(instance, validated_data)
        if units_data is not None:
            self._sync_units(product, units_data)
        return product

    def _sync_units(self, product, units_data):
        existing = {
            unit.id: unit for unit in product.unit_options.filter(deleted_at__isnull=True)
        }
        keep_ids: list[int] = []
        default_found = False

        if not units_data and product.item and product.item.unit:
            units_data = [
                {
                    'unit': product.item.unit,
                    'uom': product.item.unit.symbol or product.item.unit.code,
                    'multiplier': Decimal('1'),
                    'is_default': True,
                }
            ]

        for entry in units_data:
            if not entry:
                continue
            unit = entry.get('unit')
            multiplier = entry.get('multiplier')
            if unit is None or multiplier in (None, ''):
                continue
            if multiplier <= 0:
                raise ValidationError({'units': 'معامل التحويل يجب أن يكون أكبر من صفر.'})
            unit_id = entry.get('id')
            uom = (entry.get('uom') or getattr(unit, 'symbol', None) or getattr(unit, 'code', '') or '').strip()
            is_default = bool(entry.get('is_default'))

            if unit_id and unit_id in existing:
                unit_record = existing[unit_id]
                unit_record.unit = unit
                unit_record.multiplier = multiplier
                unit_record.uom = uom
                unit_record.is_default = is_default
                unit_record.deleted_at = None
                unit_record.save()
            else:
                unit_record = CropProductUnit.objects.create(
                    product=product,
                    unit=unit,
                    multiplier=multiplier,
                    uom=uom,
                    is_default=is_default,
                )
            keep_ids.append(unit_record.id)
            if unit_record.is_default:
                default_found = True

        if keep_ids:
            CropProductUnit.objects.filter(product=product, deleted_at__isnull=True).exclude(
                pk__in=keep_ids
            ).update(deleted_at=timezone.now())

        if keep_ids and not default_found:
            first_unit = CropProductUnit.objects.filter(product=product, pk__in=keep_ids).first()
            if first_unit:
                first_unit.is_default = True
                first_unit.save()

    def _ensure_crop_access(self, user, crop):
        if not user or not getattr(user, "is_authenticated", False):
            raise PermissionDenied("يجب تسجيل الدخول.")
        if user.is_superuser:
            return
        farm_ids = set(user_farm_ids(user))
        if not farm_ids:
            raise PermissionDenied("ليس لديك صلاحية الوصول لأي مزرعة.")
        crop_farm_ids = set(
            FarmCrop.objects.filter(crop=crop, deleted_at__isnull=True).values_list("farm_id", flat=True)
        )
        if not (farm_ids & crop_farm_ids):
            raise PermissionDenied("لا تملك صلاحية الوصول لهذا المحصول.")




class CropSerializer(serializers.ModelSerializer):
    farm = serializers.PrimaryKeyRelatedField(
        queryset=Farm.objects.all(),
        write_only=True,
        required=True,
        help_text="Farm identifier used to link the crop through FarmCrop",
    )
    farms = serializers.SerializerMethodField(read_only=True)
    
    # [DISABLED] مصفوفة المهام المدعومة - معطلة مؤقتاً حتى يتم تشغيل الـ migrations
    # supported_tasks_names = serializers.StringRelatedField(many=True, source='supported_tasks', read_only=True)
    # supported_tasks = serializers.PrimaryKeyRelatedField(
    #     many=True, 
    #     queryset=Task.objects.all(),
    #     required=False
    # )
    
    # إحصائيات للعرض
    active_plan_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Crop
        fields = [
            "id",
            "name",
            "mode",
            "is_perennial",
            "farm",
            "farms",
            # "supported_tasks",  # DISABLED - M2M table missing
            # "supported_tasks_names",  # DISABLED - M2M table missing
            "active_plan_count",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "deleted_at", "farms", "active_plan_count"]
        # [Agri-Guardian] Disable unique validator to allow "get_or_create" logic in create()
        validators = []

    def get_active_plan_count(self, obj):
        try:
            return obj.crop_plans.filter(status='active', deleted_at__isnull=True).count()
        except (ValidationError, OperationalError, ValueError) as exc:
            logger.error("Active plan count failed", exc_info=exc)
            raise

    def get_farms(self, obj):
        linked = (
            Farm.objects.filter(farm_crops__crop=obj, deleted_at__isnull=True)
            .order_by("name")
            .values("id", "name")
        )
        return list(linked)

    def _ensure_farm_access(self, farm: Farm):
        request = self.context.get("request")
        if request is None:
            return
        _ensure_user_has_farm_access(request.user, farm.id)

    def create(self, validated_data):
        farm = validated_data.pop("farm", None)
        if farm is None:
            raise ValidationError({"farm": "المزرعة مطلوبة."})
        self._ensure_farm_access(farm)
        name = validated_data.get("name")
        mode = validated_data.get("mode") or "Open"

        crop, created = Crop.objects.get_or_create(
            name=name,
            mode=mode,
            defaults=validated_data,
        )
        if not created:
            for attr, value in validated_data.items():
                setattr(crop, attr, value)
            crop.save(update_fields=list(validated_data.keys()))

        FarmCrop.objects.get_or_create(farm=farm, crop=crop)
        return crop

    def update(self, instance, validated_data):
        farm = validated_data.pop("farm", None)
        if farm is not None:
            self._ensure_farm_access(farm)
        instance = super().update(instance, validated_data)
        if farm is not None:
            FarmCrop.objects.get_or_create(farm=farm, crop=instance)
        return instance


class CropMaterialSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_group = serializers.CharField(source='item.group', read_only=True)
    item_uom = serializers.CharField(source='item.uom', read_only=True)
    item_unit_id = serializers.IntegerField(source='item.unit_id', read_only=True)
    item_unit = UnitSerializer(source='item.unit', read_only=True)
    recommended_unit = serializers.PrimaryKeyRelatedField(
        queryset=Unit.objects.filter(deleted_at__isnull=True),
        allow_null=True,
        required=False,
    )
    recommended_unit_detail = UnitSerializer(source='recommended_unit', read_only=True)

    class Meta:
        model = CropMaterial
        fields = [
            "id",
            "crop",
            "crop_name",
            "item",
            "item_name",
            "item_group",
            "item_uom",
            "item_unit_id",
            "item_unit",
            "is_primary",
            "recommended_qty",
            "recommended_uom",
            "recommended_unit",
            "recommended_unit_detail",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "crop_name",
            "item_name",
            "item_group",
            "item_uom",
            "item_unit_id",
            "item_unit",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        crop = attrs.get("crop") or getattr(self.instance, "crop", None)
        item = attrs.get("item") or getattr(self.instance, "item", None)
        if crop is None or item is None:
            raise ValidationError({"detail": "المحصول والمادة مطلوبان."})
        request = self.context.get("request")
        if request is not None:
            self._ensure_crop_access(request.user, crop)
        return attrs

    def _ensure_crop_access(self, user, crop):
        if not user or not getattr(user, "is_authenticated", False):
            raise PermissionDenied("يجب تسجيل الدخول.")
        if user.is_superuser:
            return
        farm_ids = set(user_farm_ids(user))
        if not farm_ids:
            raise PermissionDenied("ليس لديك صلاحية الوصول لأي مزرعة.")
        crop_farm_ids = set(
            FarmCrop.objects.filter(crop=crop, deleted_at__isnull=True).values_list("farm_id", flat=True)
        )
        if not (farm_ids & crop_farm_ids):
            raise PermissionDenied("لا تملك صلاحية الوصول لهذا المحصول.")


class CropTemplateMaterialSerializer(serializers.ModelSerializer):
    item_detail = serializers.SerializerMethodField()
    unit_detail = UnitSerializer(source='unit', read_only=True)

    class Meta:
        model = CropTemplateMaterial
        fields = [
            'id',
            'template',
            'item',
            'item_detail',
            'qty',
            'unit',
            'unit_detail',
            'uom',
            'cost_override',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'item_detail', 'unit_detail', 'created_at', 'updated_at']

    def get_item_detail(self, obj):
        item = getattr(obj, 'item', None)
        if not item:
            return None
        return {
            'id': item.id,
            'name': item.name,
            'group': item.group,
            'uom': item.uom,
        }


class CropTemplateTaskSerializer(serializers.ModelSerializer):
    task_detail = serializers.SerializerMethodField()

    class Meta:
        model = CropTemplateTask
        fields = [
            'id',
            'template',
            'task',
            'task_detail',
            'stage',
            'name',
            'estimated_hours',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'task_detail', 'created_at', 'updated_at']

    def get_task_detail(self, obj):
        task = getattr(obj, 'task', None)
        if not task:
            return None
        return {
            'id': task.id,
            'name': task.name,
            'stage': task.stage,
            'crop_id': task.crop_id,
            'requires_machinery': task.requires_machinery,
            'requires_well': task.requires_well,
            'requires_area': task.requires_area,
            'requires_tree_count': task.requires_tree_count,
            'is_harvest_task': task.is_harvest_task,
        }


class CropTemplateSerializer(serializers.ModelSerializer):
    materials = CropTemplateMaterialSerializer(many=True, read_only=True)
    tasks = CropTemplateTaskSerializer(many=True, read_only=True)

    class Meta:
        model = CropTemplate
        fields = [
            'id', 'name', 'crop', 'category', 'description', 
            'materials', 'tasks', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CropCardSerializer(serializers.ModelSerializer):
    """
    سيريالايزر مخصص لبطاقات العرض.
    يعيد البيانات المالية والتشغيلية المجمعة.
    """
    active_plan_count = serializers.IntegerField(read_only=True)
    total_area = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    # [SENIOR AUDITOR]: الحسابات المالية (Live Calculation)
    total_cost = serializers.SerializerMethodField()
    expected_revenue = serializers.SerializerMethodField()
    roi_percentage = serializers.SerializerMethodField()
    
    # معالجة الصور
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Crop
        fields = [
            'id', 'name', 'code', 'image', 'image_url', 'mode',
            'active_plan_count', 'total_area', 
            'total_cost', 'expected_revenue', 'roi_percentage'
        ]

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_total_cost(self, obj):
        """
        حساب التكلفة التراكمية لكل الخطط النشطة لهذا المحصول.
        """
        from decimal import Decimal
        from django.db.models import Sum
        cost = Decimal("0")
        plans = obj.plans.filter(status='active', deleted_at__isnull=True)
        for plan in plans:
            # تكلفة الأنشطة (مواد + عمالة + معدات)
            plan_cost = plan.activities.filter(deleted_at__isnull=True).aggregate(
                total=Sum('cost_total')
            )['total'] or Decimal("0")
            cost += plan_cost
        return cost

    def get_expected_revenue(self, obj):
        """
        حساب الإيراد المتوقع (مساحة * إنتاجية * سعر تقديري)
        """
        from decimal import Decimal
        from django.db.models import Sum
        revenue = obj.plans.filter(status='active', deleted_at__isnull=True).aggregate(
            total=Sum('expected_yield')
        )['total'] or Decimal("0")
        # السعر التقديري الافتراضي (يمكن تحسينه لاحقاً)
        return revenue * Decimal("1000")

    def get_roi_percentage(self, obj):
        from decimal import Decimal, ROUND_HALF_UP
        cost = self.get_total_cost(obj)
        revenue = self.get_expected_revenue(obj)
        if cost == 0:
            return Decimal("0.0")
        roi = ((revenue - cost) / cost) * Decimal("100")
        return roi.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


class CropVarietySerializer(serializers.ModelSerializer):
    crop = serializers.PrimaryKeyRelatedField(read_only=True)
    location_ids = serializers.SerializerMethodField()
    available_in_all_locations = serializers.SerializerMethodField()
    current_tree_count_total = serializers.SerializerMethodField()
    current_tree_count_by_location = serializers.SerializerMethodField()

    def get_location_ids(self, obj):
        location_map = self.context.get("variety_location_map", {})
        entry = location_map.get(obj.id) or {}
        return entry.get("location_ids", [])

    def get_available_in_all_locations(self, obj):
        location_map = self.context.get("variety_location_map", {})
        entry = location_map.get(obj.id) or {}
        return bool(entry.get("available_in_all_locations", False))

    def get_current_tree_count_total(self, obj):
        location_map = self.context.get("variety_location_map", {})
        entry = location_map.get(obj.id) or {}
        return int(entry.get("current_tree_count_total", 0) or 0)

    def get_current_tree_count_by_location(self, obj):
        location_map = self.context.get("variety_location_map", {})
        entry = location_map.get(obj.id) or {}
        return entry.get("current_tree_count_by_location", {})

    class Meta:
        model = CropVariety
        fields = [
            "id",
            "crop",
            "name",
            "code",
            "description",
            "location_ids",
            "available_in_all_locations",
            "current_tree_count_total",
            "current_tree_count_by_location",
        ]


class FarmCropSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmCrop
        fields = "__all__"

class CropRecipeTaskSerializer(serializers.ModelSerializer):
    task_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CropRecipeTask
        fields = [
            'id', 'recipe', 'task', 'task_detail', 'stage',
            'name', 'days_offset', 'estimated_hours', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'task_detail', 'created_at', 'updated_at']

    def get_task_detail(self, obj):
        task = getattr(obj, 'task', None)
        if not task:
            return None
        return {
            'id': task.id,
            'name': task.name,
            'stage': task.stage,
        }

class CropRecipeMaterialSerializer(serializers.ModelSerializer):
    item_detail = serializers.SerializerMethodField(read_only=True)
    unit_detail = UnitSerializer(source='unit', read_only=True)

    class Meta:
        model = CropRecipeMaterial
        fields = [
            'id', 'recipe', 'item', 'item_detail', 'qty',
            'unit', 'unit_detail', 'uom', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'item_detail', 'unit_detail', 'created_at', 'updated_at']

    def get_item_detail(self, obj):
        item = getattr(obj, 'item', None)
        if not item:
            return None
        return {
            'id': item.id,
            'name': item.name,
            'uom': item.uom,
        }

class CropRecipeSerializer(serializers.ModelSerializer):
    materials = CropRecipeMaterialSerializer(many=True, read_only=True)
    tasks = CropRecipeTaskSerializer(many=True, read_only=True)
    crop_name = serializers.CharField(source='crop.name', read_only=True)

    class Meta:
        model = CropRecipe
        fields = [
            'id', 'crop', 'crop_name', 'name', 'phenological_stage',
            'expected_labor_hours_per_ha', 'is_active', 'notes',
            'materials', 'tasks', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'crop_name', 'created_at', 'updated_at']
