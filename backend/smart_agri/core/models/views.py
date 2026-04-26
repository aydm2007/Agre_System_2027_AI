
from django.db import models

class FarmDashboardStats(models.Model):
    """
    Read-Only Model backed by PostgreSQL Materialized View
    Refreshed periodically for O(1) Dashboard performance.
    """
    farm = models.OneToOneField('core.Farm', on_delete=models.DO_NOTHING, primary_key=True, related_name='dashboard_stats')
    headcount = models.IntegerField()
    monthly_burn_rate = models.DecimalField(max_digits=12, decimal_places=2)
    active_plans = models.IntegerField()
    total_stock_value = models.DecimalField(max_digits=14, decimal_places=2)
    last_refreshed_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'view_farm_dashboard_stats'
        verbose_name = 'Farm Dashboard Stats'
        verbose_name_plural = 'Farm Dashboard Stats'

    @classmethod
    def refresh(cls):
        """Refreshes the materialized view."""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY view_farm_dashboard_stats;")
