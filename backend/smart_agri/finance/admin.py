from django.contrib import admin

from .models import FinancialLedger, ApprovalRequest


@admin.register(FinancialLedger)
class FinancialLedgerAdmin(admin.ModelAdmin):
    list_display = ("id", "farm", "account_code", "debit", "credit", "created_at")
    list_filter = ("farm", "account_code")
    search_fields = ("account_code", "description")

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

@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "farm", "action", "status", "requested_amount", "created_at")
    list_filter = ("status", "action", "farm")
    search_fields = ("note", "rejection_reason")

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
