from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from datetime import date
from smart_agri.core.models import Farm, Employee, EmploymentContract, Timesheet, DailyLog
from smart_agri.finance.models import FinancialLedger
from smart_agri.core.services.payroll_service import PayrollService

class HRPayrollTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin')
        self.farm = Farm.objects.create(name="Payroll Farm", slug="payroll-farm", region="Test", area=100)
        
        # 1. Hire Employee
        self.worker = Employee.objects.create(
            farm=self.farm,
            first_name="Ahmed",
            last_name="Ali",
            employee_id="E001",
            role=Employee.TYPE_WORKER,
            joined_date=date(2024, 1, 1)
        )
        
        # 2. Contract (Basic 2400 -> Hourly 10.00)
        self.contract = EmploymentContract.objects.create(
            employee=self.worker,
            start_date=date(2024, 1, 1),
            basic_salary=Decimal("2400.00"),
            housing_allowance=Decimal("400.00"),
            transport_allowance=Decimal("200.00"),
            overtime_shift_value=Decimal("0.00")
        )

    def test_payroll_cycle(self):
        """
        Verify: Timesheet -> Payroll Run -> Ledger Interaction
        """
        today = date(2024, 1, 15)
        
        # 3. Log Timesheet (10 Hours = 8 Reg + 2 OT)
        # Assuming manual entry for now or automated via DailyLog hook.
        # We test the Model first.
        Timesheet.objects.create(
            employee=self.worker,
            date=today,
            surrah_count=Decimal("1.00"),
            surrah_overtime=Decimal("0.25"),
            is_approved=True
        )
        
        # 4. Run Payroll
        # Expected:
        # Basic: 2400 (Full Month) -> In reality this service logic was simple, it gave full basic regardless of days.
        # Let's say we run for WHOLE month.
        # Allowances: 600
        # OT: Surra-based overtime value handled separately (no hourly multiplier).
        # Total: 3000.
        
        run = PayrollService.generate_payroll_run(
            self.farm, 
            date(2024, 1, 1), 
            date(2024, 1, 31), 
            self.user
        )
        
        self.assertIsNotNone(run)
        
        slip = run.slips.first()
        self.assertEqual(slip.employee, self.worker)
        self.assertEqual(slip.basic_amount, Decimal("2400.00"))
        self.assertEqual(slip.overtime_amount, Decimal("0.00"))
        self.assertEqual(slip.net_pay, Decimal("3000.00"))
        
        # 5. Approve & Check Ledger
        PayrollService.approve_run(run, self.user)
        run.refresh_from_db()
        self.assertEqual(run.status, 'Approved')
        
        # [AGRI-GUARDIAN] Assert Double-Entry: Credit Salaries Payable
        liability = FinancialLedger.objects.filter(
            account_code=FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
            credit__gt=0
        ).first()
        
        self.assertIsNotNone(liability)
        self.assertEqual(liability.credit, Decimal("3000.00"))

        # [AGRI-GUARDIAN] Assert Double-Entry: Debit Labor Expense
        expense = FinancialLedger.objects.filter(
            account_code=FinancialLedger.ACCOUNT_LABOR,
            debit__gt=0
        ).first()
        
        self.assertIsNotNone(expense, "Must create DEBIT entry for Labor Expense")
        self.assertEqual(expense.debit, Decimal("3000.00"))
        
        # [AGRI-GUARDIAN] Verify balanced
        self.assertEqual(expense.debit, liability.credit, "Double-entry must balance")

    def test_integration_activity_timesheet(self):
        """
        Verify: Activity Creation -> Auto Timesheet Generation
        """
        from smart_agri.core.models.activity import Activity
        from smart_agri.core.services.activity_service import ActivityService
        
        # 1. Create Log
        log = DailyLog.objects.create(
            farm=self.farm,
            log_date=date(2024, 2, 1),
            created_by=self.user
        )
        
        # 2. Activity Payload with Employees
        payload = {
            'log_id': log.id,
            'activity_type': 'pruning', # Assuming field exists or handled
            'cost_total': 100,
            'employees_payload': [
                {'employee_id': self.worker.id, 'surrah_share': Decimal("1.00")}
            ]
        }
        
        # 3. Call Service
        res = ActivityService.maintain_activity(self.user, payload)
        self.assertTrue(res.success)
        activity = res.data
        
        # 4. Verify ActivityEmployee
        self.assertEqual(activity.employee_details.count(), 1)
        self.assertEqual(activity.employee_details.first().surrah_share, Decimal("1.00"))
        
        # 5. Verify Timesheet (Auto-Generated)
        ts = Timesheet.objects.filter(employee=self.worker, date=date(2024, 2, 1)).first()
        self.assertIsNotNone(ts)
        self.assertEqual(ts.surrah_count, Decimal("1.00"))
        self.assertEqual(ts.activity, activity)
