"""Serializers for Partnership models (Sharecropping & Touring)."""

from rest_framework import serializers
from smart_agri.core.models.partnerships import (
    SharecroppingContract, TouringAssessment, SharecroppingReceipt
)


class SharecroppingContractSerializer(serializers.ModelSerializer):
    """Serializer for sharecropping/rental contracts."""
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    crop_name = serializers.CharField(source='crop.name', read_only=True)
    zakat_rate = serializers.SerializerMethodField()

    class Meta:
        model = SharecroppingContract
        fields = [
            'id', 'farm', 'farm_name',
            'farmer_name', 'farmer_id_number',
            'crop', 'crop_name', 'season',
            'contract_type', 'irrigation_type',
            'institution_percentage', 'annual_rent_amount',
            'is_active', 'notes', 'zakat_rate',
            'created_at',
        ]

    def get_zakat_rate(self, obj):
        return str(obj.get_zakat_rate())


class TouringAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for touring assessments."""
    farmer_name = serializers.CharField(
        source='contract.farmer_name', read_only=True,
    )
    farm_name = serializers.CharField(
        source='contract.farm.name', read_only=True,
    )

    class Meta:
        model = TouringAssessment
        fields = [
            'id', 'contract', 'farmer_name', 'farm_name',
            'assessment_date',
            'estimated_total_yield_kg',
            'expected_zakat_kg',
            'expected_institution_share_kg',
            'committee_members',
            'is_harvested', 'notes', 'created_at',
        ]
        read_only_fields = [
            'assessment_date', 'expected_zakat_kg',
            'expected_institution_share_kg', 'created_at',
        ]

class SharecroppingReceiptSerializer(serializers.ModelSerializer):
    """Serializer for sharecropping receipts (physical or financial)."""
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    farmer_name = serializers.CharField(source='assessment.contract.farmer_name', read_only=True)
    destination_inventory_name = serializers.CharField(source='destination_inventory.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.get_full_name', read_only=True)

    class Meta:
        model = SharecroppingReceipt
        fields = [
            'id', 'farm', 'farm_name', 'assessment', 'farmer_name',
            'receipt_date', 'receipt_type',
            'amount_received', 'quantity_received_kg',
            'destination_inventory', 'destination_inventory_name',
            'received_by', 'received_by_name',
            'is_posted', 'notes', 'created_at'
        ]
        read_only_fields = ['is_posted', 'created_at']
