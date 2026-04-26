from decimal import Decimal

from rest_framework import serializers
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO
from PIL import Image
import sys
from smart_agri.core.models.log import DailyLog
from django.core.exceptions import ValidationError
from django.db import OperationalError

class CompressedImageField(serializers.ImageField):
    """
    [AGRI-GUARDIAN] AgriAsset Yemen: Aggressive Compression.
    Ensures no image exceeds 100KB to survive 2G upload speeds.
    Protocol XXVII: The 2G Survival Standard.
    """
    def to_internal_value(self, data):
        # Determine strict limit based on network context
        MAX_SIZE_KB = 100
        
        # If data is already a file (Multipart), check size
        if data.size > MAX_SIZE_KB * 1024:
            try:
                img = Image.open(data)
                output = BytesIO()
                
                # Remove metadata, convert to JPEG, degrade quality
                img = img.convert('RGB')
                
                # Optimization loop
                quality = 70
                while quality > 10:
                    output.seek(0)
                    output.truncate(0)
                    img.save(output, format='JPEG', quality=quality, optimize=True)
                    if output.tell() <= MAX_SIZE_KB * 1024:
                        break
                    quality -= 10
                
                output.seek(0)
                
                data = InMemoryUploadedFile(
                    output, 
                    'ImageField', 
                    f"{data.name.split('.')[0]}.jpg",
                    'image/jpeg', 
                    sys.getsizeof(output), 
                    None
                )
            except (ValidationError, OperationalError, ValueError) as e:
                # Fallback or Log error, but don't crash
                pass

        return super().to_internal_value(data)

class DailyLogImageSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for uploading receipt/issue images.
    Uses Multipart/Form-Data, NOT Base64.
    """
    receipt_image = CompressedImageField(write_only=True, required=False)
    
    class Meta:
        model = DailyLog
        fields = ['id', 'notes', 'receipt_image']

class DailyLogBasicSerializer(serializers.ModelSerializer):
    """
    Basic/Lite serializer for embedding in other representations (e.g. Activity).
    Prevents circular recursion depth.
    """
    class Meta:
        model = DailyLog
        fields = ('id', 'log_date', 'status', 'farm', 'supervisor')

# [AGRI-GUARDIAN] Stubs to satisfy missing imports
from smart_agri.core.models.log import AuditLog, Attachment, SyncRecord
from smart_agri.core.models.settings import Supervisor
from smart_agri.core.models.sync_conflict import OfflineSyncQuarantine, SyncConflictDLQ

class DailyLogSerializer(serializers.ModelSerializer):
    material_governance_blocked = serializers.SerializerMethodField()
    missing_price_governance = serializers.SerializerMethodField()
    material_governance_reasons = serializers.SerializerMethodField()

    # [UI] Human-readable user names for Timeline display
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    # [UI] Count of activities for sidebar badge
    activity_count = serializers.SerializerMethodField()

    class Meta:
        model = DailyLog
        fields = '__all__'

    def _get_user_display(self, user):
        if user is None:
            return None
        full_name = (user.get_full_name() or '').strip()
        return full_name if full_name else user.username

    def get_created_by_name(self, obj):
        return self._get_user_display(obj.created_by)

    def get_updated_by_name(self, obj):
        return self._get_user_display(obj.updated_by)

    def get_approved_by_name(self, obj):
        return self._get_user_display(obj.approved_by)

    def get_activity_count(self, obj):
        return obj.activities.filter(deleted_at__isnull=True).count()

    def _compute_material_governance_reasons(self, obj):
        reasons = []
        activities = obj.activities.filter(deleted_at__isnull=True).prefetch_related('items__item') if getattr(obj, 'pk', None) else []
        for activity in activities:
            for usage in activity.items.all():
                item = getattr(usage, 'item', None)
                if item is None:
                    continue
                unit_price = getattr(item, 'unit_price', None)
                if unit_price is not None and Decimal(str(unit_price)) <= Decimal('0'):
                    reasons.append({
                        'flag': 'missing_price',
                        'item_id': item.id,
                        'item_name': item.name,
                        'activity_id': activity.id,
                    })
                if getattr(item, 'requires_batch_tracking', False) and not (getattr(usage, 'batch_number', '') or '').strip():
                    reasons.append({
                        'flag': 'missing_batch_tracking',
                        'item_id': item.id,
                        'item_name': item.name,
                        'activity_id': activity.id,
                    })
        return reasons

    def get_material_governance_reasons(self, obj):
        return self._compute_material_governance_reasons(obj)

    def get_material_governance_blocked(self, obj):
        return bool(self._compute_material_governance_reasons(obj))

    def get_missing_price_governance(self, obj):
        return any(reason.get('flag') == 'missing_price' for reason in self._compute_material_governance_reasons(obj))

class SupervisorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supervisor
        fields = '__all__'

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = '__all__'

    def validate(self, attrs):
        request = self.context.get("request") if hasattr(self, "context") else None
        file_obj = attrs.get("file")
        evidence_class = attrs.get("evidence_class", Attachment.EVIDENCE_CLASS_OPERATIONAL)

        if request:
            # Required metadata by V21 policy
            attrs.setdefault("uploaded_by", getattr(request, "user", None))

            # Resolve farm scope
            farm_id = (
                request.query_params.get("farm")
                or request.query_params.get("farm_id")
                or request.headers.get("X-Farm-Id")
            )
            if not farm_id:
                # If user has exactly one farm membership, infer it.
                try:
                    from smart_agri.core.api.permissions import user_farm_ids
                    farm_ids = user_farm_ids(request.user)
                    if len(farm_ids) == 1:
                        farm_id = str(farm_ids[0])
                except (ImportError, AttributeError, ValueError, TypeError):
                    farm_id = None
            if farm_id:
                attrs.setdefault("farm_id", int(farm_id))
            else:
                # Fall back to explicit document scope (still required by matrix)
                attrs.setdefault("document_scope", f"user:{getattr(request.user, 'id', 'unknown')}:unscoped")

            # Related document type is required by matrix; accept client-provided hint or default.
            related_type = (
                request.query_params.get("related_document_type")
                or request.data.get("related_document_type")
                or request.query_params.get("doc_type")
                or "unspecified"
            )
            attrs.setdefault("related_document_type", related_type)

            # Class/retention mirror
            attrs.setdefault("attachment_class", evidence_class)
            attrs.setdefault("retention_class", evidence_class)

        if request and file_obj is not None:
            from smart_agri.core.models.settings import FarmSettings
            from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService
            farm_settings = FarmSettings.objects.filter(farm_id=attrs.get("farm_id")).first() if attrs.get("farm_id") else None
            policy = AttachmentPolicyService.validate_upload(
                farm_settings=farm_settings,
                file_obj=file_obj,
                evidence_class=evidence_class,
            )
            attrs.setdefault("expires_at", policy.get("expires_at"))
            attrs.setdefault("content_type", policy.get("content_type", attrs.get("content_type", "")))
            attrs.setdefault("mime_type_detected", policy.get("mime_type_detected", attrs.get("mime_type_detected", "")))
            attrs.setdefault("storage_tier", policy.get("storage_tier"))
            attrs.setdefault("archive_state", policy.get("archive_state", getattr(Attachment, "ARCHIVE_STATE_HOT", "hot")))
            attrs.setdefault("malware_scan_status", policy.get("malware_scan_status"))
            attrs.setdefault("scan_state", policy.get("scan_state", policy.get("malware_scan_status")))
            attrs.setdefault("sha256_checksum", policy.get("sha256_checksum", attrs.get("sha256_checksum", "")))
            attrs.setdefault("content_hash", policy.get("content_hash", attrs.get("content_hash", "")))
            attrs.setdefault("filename_original", policy.get("filename_original", getattr(file_obj, "name", "") or ""))
            attrs.setdefault("size", getattr(file_obj, "size", 0) or 0)
            attrs.setdefault("size_bytes", policy.get("size_bytes", int(getattr(file_obj, "size", 0) or 0)))
        return attrs

class AuditLogSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id', 'action', 'model', 'object_id',
            'actor', 'user_details',
            'new_payload', 'old_payload', 'reason',
            'timestamp'
        ]
        read_only_fields = fields

    def get_user_details(self, obj):
        if not obj.actor:
            return None
        return {
            "id": obj.actor.id,
            "username": obj.actor.username,
            "full_name": obj.actor.get_full_name() or obj.actor.username
        }

class SyncRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncRecord
        fields = '__all__'


class SyncConflictDLQSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    actor_username = serializers.CharField(source='actor.username', read_only=True)

    class Meta:
        model = SyncConflictDLQ
        fields = '__all__'


class OfflineSyncQuarantineSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    manager_signature_username = serializers.CharField(source='manager_signature.username', read_only=True)

    class Meta:
        model = OfflineSyncQuarantine
        fields = '__all__'

from smart_agri.core.models.log import MaterialVarianceAlert

class MaterialVarianceAlertSerializer(serializers.ModelSerializer):
    log_date = serializers.CharField(source='log.log_date', read_only=True)
    farm_name = serializers.CharField(source='log.farm.name', read_only=True)
    crop_plan_name = serializers.CharField(source='crop_plan.name', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_uom = serializers.CharField(source='item.uom', read_only=True)
    supervisor_name = serializers.CharField(source='log.supervisor.name', read_only=True)

    class Meta:
        model = MaterialVarianceAlert
        fields = '__all__'
