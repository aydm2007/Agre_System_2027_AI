"""
Season Serializer
"""
from rest_framework import serializers
from smart_agri.core.models import Season


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = "__all__"
