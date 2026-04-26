"""
Unit Serializers
"""
from rest_framework import serializers
from smart_agri.core.models import Unit, UnitConversion


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = [
            'id',
            'code',
            'name',
            'symbol',
            'category',
            'precision',
            'metadata',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UnitConversionSerializer(serializers.ModelSerializer):
    from_unit_detail = UnitSerializer(source='from_unit', read_only=True)
    to_unit_detail = UnitSerializer(source='to_unit', read_only=True)

    class Meta:
        model = UnitConversion
        fields = [
            'id',
            'from_unit',
            'from_unit_detail',
            'to_unit',
            'to_unit_detail',
            'multiplier',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'from_unit_detail', 'to_unit_detail']
