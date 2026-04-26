"""
Asset Serializer Module
"""
from rest_framework import serializers
from smart_agri.core.models import Asset


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = "__all__"
