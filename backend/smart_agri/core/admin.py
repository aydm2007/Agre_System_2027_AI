from django.contrib import admin
from .models import (
    Attachment, DailyLog, Activity, ActivityItem, Item,
    HarvestLot, Farm, Location, Asset, Crop,
    LocationIrrigationPolicy,
    FarmCrop, Task, Supervisor, AuditLog,
    Season, CropPlan, CropPlanBudgetLine, ActivityCostSnapshot,
    IntegrationOutboxEvent, LocationTreeStock, CropVariety
)


class SoftDeleteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "created_at", "updated_at", "deleted_at")
    list_filter = ("deleted_at",)
    search_fields = ("__str__",)
    actions = ["restore"]

    def get_queryset(self, request):
        if request.user.is_superuser:
            # Bypass RLS and FarmScopedManager for superusers in the admin interface
            return self.model._base_manager.all()
        return super().get_queryset(request).all()

    def restore(self, request, queryset):
        updated = queryset.update(deleted_at=None)
        self.message_user(request, f"Restored {updated} records.")

# سجل الموديلات التي تحتاج SoftDeleteAdmin
for m in (Farm, Location, Asset, Crop, FarmCrop, Task, Supervisor, ActivityItem, LocationTreeStock, CropVariety):
    admin.site.register(m, SoftDeleteAdmin)

admin.site.register(LocationIrrigationPolicy, SoftDeleteAdmin)

# سجل باقي الموديلات مرة واحدة فقط
admin.site.register(AuditLog)
admin.site.register(HarvestLot)

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'farm', 'name', 'evidence_class', 'malware_scan_status', 'created_at')
    list_filter = ('evidence_class', 'malware_scan_status', 'storage_tier')
    search_fields = ('name', 'filename_original', 'sha256_checksum')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [field.name for field in self.model._meta.fields]
        return []

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'group', 'unit', 'unit_price')
    list_filter = ('group', 'deleted_at')
    search_fields = ('name', 'group')

class ActivityItemInline(admin.TabularInline):
    model = ActivityItem
    extra = 1
    autocomplete_fields = ['item']

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'log', 'task', 'cost_total', 'created_at')
    list_filter = ('task', 'log__log_date')
    search_fields = ('notes', 'log__id')
    inlines = [ActivityItemInline]
    readonly_fields = ('cost_total',)


@admin.register(CropPlanBudgetLine)
class CropPlanBudgetLineAdmin(admin.ModelAdmin):
    list_display = ('crop_plan', 'category', 'total_budget')
    list_filter = ('category',)

@admin.register(ActivityCostSnapshot)
class ActivityCostSnapshotAdmin(admin.ModelAdmin):
    list_display = ('activity', 'snapshot_at', 'cost_total')
    readonly_fields = ('snapshot_at',)


# ─── YECO Hybrid ERP: Shadow Mode Admin ─────────────────────────────
from .models.settings import SystemSettings
from .models.report import VarianceAlert


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('strict_erp_mode', 'allowed_variance_percentage',
                    'diesel_tolerance_percentage', 'updated_at', 'updated_by')
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        """Singleton: prevent adding if one already exists."""
        return not SystemSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Singleton: never allow deletion."""
        return False


@admin.register(VarianceAlert)
class VarianceAlertAdmin(admin.ModelAdmin):
    list_display = ('farm', 'category', 'activity_name',
                    'variance_percentage', 'status', 'created_at')
    list_filter = ('status', 'category', 'farm')
    search_fields = ('activity_name', 'alert_message')
    readonly_fields = ('farm', 'daily_log', 'category', 'activity_name',
                       'planned_cost', 'actual_cost', 'variance_amount',
                       'variance_percentage', 'alert_message', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(IntegrationOutboxEvent)
class IntegrationOutboxEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'event_type', 'aggregate_type', 'aggregate_id', 'farm', 'status', 'attempts', 'available_at', 'dispatched_at')
    list_filter = ('status', 'event_type', 'aggregate_type', 'farm')
    search_fields = ('event_id', 'aggregate_id', 'last_error')
    readonly_fields = ('event_id', 'payload', 'metadata', 'attempts', 'last_error', 'created_at', 'updated_at', 'locked_at', 'locked_by', 'dispatched_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
