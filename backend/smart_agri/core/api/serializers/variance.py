"""Serializers for VarianceAlert (Shadow Variance Radar Dashboard)."""

from rest_framework import serializers
from smart_agri.core.models.report import VarianceAlert


class VarianceAlertSerializer(serializers.ModelSerializer):
    """
    تجهيز بيانات إنذارات الظل (Shadow Alerts) للوحة قيادة الإدارة.
    """
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True,
    )
    category_display = serializers.CharField(
        source='get_category_display', read_only=True,
    )

    class Meta:
        model = VarianceAlert
        fields = [
            'id', 'farm', 'farm_name', 'daily_log',
            'category', 'category_display',
            'activity_name',
            'planned_cost', 'actual_cost',
            'variance_amount', 'variance_percentage',
            'alert_message',
            'status', 'status_display',
            'resolved_by', 'resolved_at', 'resolution_note',
            'created_at',
        ]
        read_only_fields = [
            'id', 'farm', 'farm_name', 'daily_log',
            'category', 'activity_name',
            'planned_cost', 'actual_cost',
            'variance_amount', 'variance_percentage',
            'alert_message', 'created_at',
        ]
