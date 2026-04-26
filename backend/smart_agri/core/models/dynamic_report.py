from django.db import models
from smart_agri.core.models.base import SoftDeleteModel
from smart_agri.core.models.farm import Farm

class ReportTemplate(SoftDeleteModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="report_templates")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=20, choices=[
        ('table', 'جدول'),
        ('chart', 'رسم بياني'),
        ('pivot', 'Pivot Table')
    ])
    model_name = models.CharField(max_length=100, help_text="اسم الـ Model المراد الاستعلام منه")
    fields = models.JSONField(default=list, help_text="الحقول المراد عرضها")
    filters = models.JSONField(default=dict, blank=True, help_text="شروط التصفية")
    group_by = models.JSONField(default=list, blank=True)
    aggregation = models.JSONField(default=dict, blank=True)
    chart_config = models.JSONField(default=dict, blank=True)
    is_public = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "قالب تقرير ديناميكي"
        verbose_name_plural = "قوالب التقارير الديناميكية"

class SavedReport(SoftDeleteModel):
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name="saved_instances")
    parameters = models.JSONField(default=dict, blank=True)
    result_data = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "تقرير محفوظ"
        verbose_name_plural = "التقارير المحفوظة"
