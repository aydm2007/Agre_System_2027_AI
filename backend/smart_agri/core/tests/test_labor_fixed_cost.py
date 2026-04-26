import pytest
from decimal import Decimal
from smart_agri.core.models.activity import Activity, ActivityEmployee
from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.farm import Farm
from smart_agri.core.services.activity_labor import sync_activity_employees
from django.utils import timezone
from django.core.exceptions import ValidationError

@pytest.mark.django_db
class TestLaborFixedCost:
    def test_sync_with_fixed_wage_cost(self):
        # 1. Setup
        farm = Farm.objects.create(name="Test Farm")
        log = DailyLog.objects.create(farm=farm, log_date=timezone.localdate())
        activity = Activity.objects.create(log=log)
        
        # 2. Payload with fixed cost
        payload = [
            {
                "labor_type": "CASUAL_BATCH",
                "workers_count": 10,
                "surrah_share": 1.0,
                "fixed_wage_cost": "5500.00"
            }
        ]
        
        # 3. Execution (sync_activity_employees normally runs in a session where ActivityEmployee is imported)
        sync_activity_employees(activity, payload)
        
        # 4. Verification
        emp_detail = ActivityEmployee.objects.get(activity=activity)
        assert emp_detail.fixed_wage_cost == Decimal("5500.0000")
        assert emp_detail.wage_cost == Decimal("5500.0000")
        # Surrah share should still exist as metadata (1.0 * 10 = 10)
        assert emp_detail.surrah_share == Decimal("10.00")

    def test_sync_with_illogical_fixed_wage_cost(self):
        # Setup
        farm = Farm.objects.create(name="Anomaly Farm")
        # Ensure standard cost is known (e.g. 500 YER/day * 1 worker * 1 surra = 500)
        # Note: If no rate exists, standard_cost is 0 and validation is skipped for now
        # But we assume the farm has a rate for this test.
        log = DailyLog.objects.create(farm=farm, log_date=timezone.localdate())
        activity = Activity.objects.create(log=log)
        
        # Payload with extreme cost (standard would be ~500, we send 100,000)
        payload = [
            {
                "labor_type": "CASUAL_BATCH",
                "workers_count": 1,
                "surrah_share": 1.0,
                "fixed_wage_cost": "100000.00" 
            }
        ]
        
        with pytest.raises(ValidationError) as excinfo:
            sync_activity_employees(activity, payload)
        
        assert "غير منطقي" in str(excinfo.value)

    def test_sync_without_fixed_wage_cost_uses_default(self):
         # Setup
        farm = Farm.objects.create(name="Test Farm 2")
        log = DailyLog.objects.create(farm=farm, log_date=timezone.localdate())
        activity = Activity.objects.create(log=log)
        
        payload = [
            {
                "labor_type": "CASUAL_BATCH",
                "workers_count": 10,
                "surrah_share": 1.0,
                # No fixed_wage_cost
            }
        ]
        
        sync_activity_employees(activity, payload)
        
        emp_detail = ActivityEmployee.objects.get(activity=activity)
        assert emp_detail.fixed_wage_cost is None
