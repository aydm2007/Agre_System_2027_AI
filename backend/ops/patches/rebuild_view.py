import os
import django
import sys
from django.db import connection

# Setup Django
sys.path.append(r'C:\tools\workspace\AgriAsset_v44_test\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

def rebuild_dashboard_view():
    print("💎 [SOVEREIGN FIX] Reconstructing Materialized View: view_farm_dashboard_stats...")
    
    sql = """
        DROP MATERIALIZED VIEW IF EXISTS view_farm_dashboard_stats;
        CREATE MATERIALIZED VIEW view_farm_dashboard_stats AS
        SELECT
            f.id AS farm_id,
            COALESCE(emp_stats.headcount, 0) AS headcount,
            COALESCE(emp_stats.burn_rate, 0) AS monthly_burn_rate,
            (SELECT COUNT(*) 
             FROM core_cropplan cp 
             WHERE cp.farm_id = f.id AND cp.status = 'active'
            ) AS active_plans,
            (SELECT COALESCE(SUM(inv.qty * item.unit_price), 0)
             FROM core_item_inventory inv
             JOIN core_item item ON inv.item_id = item.id
             WHERE inv.farm_id = f.id
            ) AS total_stock_value,
            NOW() AS last_refreshed_at
        FROM core_farm f
        LEFT JOIN (
            SELECT 
                e.farm_id, 
                COUNT(e.id) AS headcount, 
                SUM(COALESCE(c.basic_salary, 0) + COALESCE(c.housing_allowance, 0) + COALESCE(c.transport_allowance, 0) + COALESCE(c.other_allowance, 0)) AS burn_rate
            FROM core_employee e
            JOIN core_employmentcontract c ON e.id = c.employee_id
            WHERE e.is_active = TRUE AND c.is_active = TRUE
            GROUP BY e.farm_id
        ) emp_stats ON f.id = emp_stats.farm_id;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_view_farm_stats_farm_id ON view_farm_dashboard_stats (farm_id);
    """
    
    with connection.cursor() as cursor:
        cursor.execute(sql)
    
    print("✅ Materialized View successfully reconstructed.")

if __name__ == "__main__":
    rebuild_dashboard_view()
