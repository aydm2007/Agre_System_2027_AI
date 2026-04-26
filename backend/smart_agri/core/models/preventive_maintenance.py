from django.db import models
from smart_agri.core.models.base import SoftDeleteModel
from smart_agri.core.models.farm import Farm, Asset
from smart_agri.core.models.hr import Employee

class MaintenanceSchedule(SoftDeleteModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="maintenance_schedules")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="maintenance_schedules")
    name = models.CharField(max_length=100)
    frequency_type = models.CharField(max_length=20, choices=[
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('meter', 'حسب العداد (ساعات/كم)')
    ])
    frequency_value = models.IntegerField(default=1)
    meter_threshold = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    last_performed = models.DateField(null=True, blank=True)
    next_due = models.DateField(null=True, blank=True)
    instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "جدول صيانة وقائية"
        verbose_name_plural = "جداول الصيانة الوقائية"

class MaintenanceTask(SoftDeleteModel):
    schedule = models.ForeignKey(MaintenanceSchedule, on_delete=models.CASCADE, related_name='tasks')
    description = models.CharField(max_length=200)
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    due_date = models.DateField()
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'قيد الانتظار'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('overdue', 'متأخر')
    ])
    
    class Meta:
        verbose_name = "مهمة صيانة"
        verbose_name_plural = "مهام الصيانة"
