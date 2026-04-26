
from django.contrib import admin
from .models import FarmMembership
@admin.register(FarmMembership)
class FarmMembershipAdmin(admin.ModelAdmin):
    list_display = ("user","farm","role")
    search_fields = ("user__username","farm__name","role")
    list_filter = ("role",)
