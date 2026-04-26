"""
Item Serializer
"""
from rest_framework import serializers
from smart_agri.core.models import Item
from .unit import UnitSerializer


class ItemSerializer(serializers.ModelSerializer):
    unit_detail = UnitSerializer(source='unit', read_only=True)
    material_type_display = serializers.CharField(source='get_material_type_display', read_only=True)

    class Meta:
        model = Item
        fields = [
            'id',
            'name',
            'group',
            'material_type',
            'material_type_display',
            'uom',
            'unit',
            'unit_detail',
            'unit_price',
            'currency',
            'reorder_level',
            'requires_batch_tracking',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'unit_detail']
        extra_kwargs = {
            'uom': {'required': False, 'allow_blank': True},
            'currency': {'required': False},
            'unit_price': {'required': False},
            'reorder_level': {'required': False},
            'requires_batch_tracking': {'required': False},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        provided_unit = attrs.get('unit') or getattr(self.instance, 'unit', None)
        provided_uom = attrs.get('uom') or getattr(self.instance, 'uom', '')
        if not provided_unit and not provided_uom:
            raise serializers.ValidationError({'unit': 'يجب تحديد الوحدة الفنية أو رمز وحدة القياس.'})
        if provided_uom:
            attrs['uom'] = provided_uom.strip()
        elif provided_unit:
            attrs['uom'] = (getattr(provided_unit, 'symbol', '') or getattr(provided_unit, 'code', '') or '').strip()
        if 'currency' in attrs and attrs['currency']:
            attrs['currency'] = attrs['currency'].upper()[:8]
        unit_price = attrs.get('unit_price')
        if unit_price is not None and unit_price < 0:
            raise serializers.ValidationError({'unit_price': 'سعر الوحدة لا يمكن أن يكون سالبًا.'})
        reorder_level = attrs.get('reorder_level')
        if reorder_level is not None and reorder_level < 0:
            raise serializers.ValidationError({'reorder_level': 'حد إعادة الطلب لا يمكن أن يكون سالبًا.'})
        return attrs
