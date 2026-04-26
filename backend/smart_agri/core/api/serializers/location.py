"""
Location Serializer Module
"""
from rest_framework import serializers
from smart_agri.core.models import Location


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"
