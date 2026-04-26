from django.db import models
from django.utils import timezone
from django.conf import settings

# TextChoices moved to core.constants to prevent circular imports

class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.exclude(deleted_at__isnull=True)

    def delete(self):
        """
        Bulk soft delete.
        """
        return super().update(deleted_at=timezone.now())

class AgriAssetBaseModel(models.Model):
    """
    AgriAsset Forensic Base: Nothing is ever truly deleted.
    Protocol XXV: The Immortal Data Standard.
    """
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(null=True, default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(null=True, default=timezone.now)
    
    # Forensic Audit Trail
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+', blank=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """
        Soft Delete Logic.
        Overrides standard Django delete to prevent data loss.
        """
        self.is_active = False
        self.deleted_at = timezone.now()
        # self.deleted_by should ideally be set by the caller/service layer
        self.save(update_fields=["deleted_at", "is_active", "updated_at"], using=using)

    def hard_delete_forensic(self):
        """
        Only accessible by SuperAdmin via distinct command.
        Actually removes data from disk.
        """
        super().delete()

# Alias for backward compatibility if needed, but new code should use AgriAssetBaseModel
SoftDeleteModel = AgriAssetBaseModel
