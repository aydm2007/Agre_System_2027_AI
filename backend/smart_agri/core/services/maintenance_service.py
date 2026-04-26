from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db import transaction
from smart_agri.core.models.preventive_maintenance import MaintenanceSchedule, MaintenanceTask

class MaintenanceService:
    def __init__(self, farm):
        self.farm = farm
    
    @transaction.atomic
    def generate_due_tasks(self):
        """توليد مهام الصيانة المستحقة بناءً على الجداول"""
        # جلب الجداول التي استحق تاريخ تنفيذها القادم
        schedules = MaintenanceSchedule.objects.filter(
            farm=self.farm,
            is_active=True
        ).exclude(next_due__gt=timezone.now().date())
        
        created_tasks = []
        for schedule in schedules:
            task = MaintenanceTask.objects.create(
                schedule=schedule,
                description=f"صيانة وقائية دورية: {schedule.name}",
                due_date=schedule.next_due or timezone.now().date(),
                status='pending'
            )
            
            # تحديث تاريخ الاستحقاق القادم في الجدول
            if schedule.frequency_type == 'daily':
                schedule.next_due = (schedule.next_due or timezone.now().date()) + timedelta(days=schedule.frequency_value)
            elif schedule.frequency_type == 'weekly':
                schedule.next_due = (schedule.next_due or timezone.now().date()) + timedelta(weeks=schedule.frequency_value)
            elif schedule.frequency_type == 'monthly':
                schedule.next_due = (schedule.next_due or timezone.now().date()) + timedelta(days=30 * schedule.frequency_value)
            
            schedule.last_performed = timezone.now().date()
            schedule.save()
            created_tasks.append(task)
            
        return created_tasks
    
    def get_dashboard_summary(self):
        """إحصائيات لوحة الصيانة"""
        from django.db.models import Count
        tasks = MaintenanceTask.objects.filter(schedule__farm=self.farm)
        
        status_counts = tasks.values('status').annotate(count=Count('id'))
        pending = sum(c['count'] for c in status_counts if c['status'] == 'pending')
        completed = sum(c['count'] for c in status_counts if c['status'] == 'completed')
        
        overdue = MaintenanceTask.objects.filter(
            schedule__farm=self.farm,
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'in_progress']
        ).count()
        
        return {
            'pending_tasks': pending,
            'completed_tasks': completed,
            'overdue_tasks': overdue,
            'maintenance_health_score': self._calculate_health(completed, pending + completed)
        }
        
    def _calculate_health(self, completed, total):
        if total == 0:
            return 100
        ratio = (
            Decimal(str(completed)) / Decimal(str(total))  # agri-guardian: decimal-safe
        ) * Decimal("100")
        return int(ratio.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
