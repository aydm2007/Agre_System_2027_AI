"""
[Gap #7] Unit Tests for HR Services.

Covers:
  - TimesheetService (create, approve, monthly_summary)
  - AdvancesService (create, approve, deduct, idempotency)
  - PayrollService (generate, approve, advance integration)
  - WorkerProductivityService (get_labor_kpi)
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from smart_agri.core.models.hr import (
    Employee, EmploymentCategory, Timesheet, PayrollRun, PayrollSlip,
    EmployeeAdvance, AdvanceStatus, PayrollStatus,
)
from smart_agri.core.models.farm import Farm

User = get_user_model()


class TimesheetServiceTest(TestCase):
    """Tests for TimesheetService — Axis 5, 6, 7."""

    @classmethod
    def setUpTestData(cls):
        cls.farm = Farm.objects.create(name="TS Farm", slug="ts-farm-test")
        cls.user = User.objects.create_user(username="ts_approver", password="test1234")
        cls.employee = Employee.objects.create(
            farm=cls.farm,
            first_name="أحمد",
            last_name="محمد",
            employee_id="TS-EMP-001",
            category=EmploymentCategory.CASUAL,
            shift_rate=Decimal("500.0000"),
        )

    def test_record_manual_timesheet(self):
        """[Axis 5] Manual timesheet uses Decimal, creates entry."""
        from smart_agri.core.services.timesheet_service import TimesheetService
        ts = TimesheetService.record_manual_timesheet(
            employee_id=self.employee.id,
            farm_id=self.farm.id,
            date=date(2026, 3, 1),
            surrah_count="1.00",
            surrah_overtime="0.25",
        )
        self.assertEqual(ts.surrah_count, Decimal("1.00"))
        self.assertEqual(ts.surrah_overtime, Decimal("0.25"))
        self.assertEqual(ts.farm_id, self.farm.id)

    def test_record_manual_rejects_wrong_farm(self):
        """[Axis 6] Rejects employee from different farm."""
        from smart_agri.core.services.timesheet_service import TimesheetService
        other_farm = Farm.objects.create(name="Other Farm TS", slug="other-farm-ts")
        with self.assertRaises(ValidationError) as ctx:
            TimesheetService.record_manual_timesheet(
                employee_id=self.employee.id,
                farm_id=other_farm.id,
                date=date(2026, 3, 1),
                surrah_count="1.00",
            )
        self.assertIn("employee_id", ctx.exception.message_dict)

    def test_record_manual_rejects_zero_surrah(self):
        """[Axis 5] Rejects zero surrah."""
        from smart_agri.core.services.timesheet_service import TimesheetService
        with self.assertRaises(ValidationError):
            TimesheetService.record_manual_timesheet(
                employee_id=self.employee.id,
                farm_id=self.farm.id,
                date=date(2026, 3, 1),
                surrah_count="0",
            )

    def test_approve_timesheet(self):
        """[Axis 7] Approval sets is_approved and approved_by."""
        from smart_agri.core.services.timesheet_service import TimesheetService
        ts = Timesheet.objects.create(
            employee=self.employee, farm=self.farm,
            date=date(2026, 3, 1), surrah_count=Decimal("1.00"),
            surrah_overtime=Decimal("0.00"), is_approved=False,
        )
        approved = TimesheetService.approve_timesheet(ts.id, self.user)
        self.assertTrue(approved.is_approved)
        self.assertEqual(approved.approved_by, self.user)

    def test_approve_timesheet_idempotent(self):
        """[Axis 2] Approving already-approved timesheet returns same object."""
        from smart_agri.core.services.timesheet_service import TimesheetService
        ts = Timesheet.objects.create(
            employee=self.employee, farm=self.farm,
            date=date(2026, 3, 2), surrah_count=Decimal("1.00"),
            surrah_overtime=Decimal("0.00"), is_approved=True,
            approved_by=self.user,
        )
        result = TimesheetService.approve_timesheet(ts.id, self.user)
        self.assertTrue(result.is_approved)

    def test_monthly_summary(self):
        """[Axis 5/6] Monthly summary returns Decimal strings and costs."""
        from smart_agri.core.services.timesheet_service import TimesheetService
        Timesheet.objects.create(
            employee=self.employee, farm=self.farm,
            date=date(2026, 3, 1), surrah_count=Decimal("1.00"),
            surrah_overtime=Decimal("0.50"), is_approved=True,
        )
        Timesheet.objects.create(
            employee=self.employee, farm=self.farm,
            date=date(2026, 3, 2), surrah_count=Decimal("0.75"),
            surrah_overtime=Decimal("0.00"), is_approved=False,
        )
        result = TimesheetService.get_monthly_summary(self.farm.id, 2026, 3)
        self.assertEqual(len(result['employees']), 1)
        emp = result['employees'][0]
        self.assertEqual(emp['total_surrah'], '1.75')
        self.assertIn('estimated_cost', emp)
        self.assertIn('budget', result)


class AdvancesServiceTest(TestCase):
    """Tests for AdvancesService — Axis 2, 4, 5, 6, 7."""

    @classmethod
    def setUpTestData(cls):
        cls.farm = Farm.objects.create(name="Advance Farm", slug="advance-farm-test")
        cls.user = User.objects.create_user(username="adv_approver", password="test1234")
        cls.employee = Employee.objects.create(
            farm=cls.farm,
            first_name="علي",
            last_name="سعيد",
            employee_id="ADV-001",
            category=EmploymentCategory.CASUAL,
            shift_rate=Decimal("500.0000"),
        )

    def test_create_advance(self):
        """[Axis 5/6] Creates advance with Decimal amount."""
        from smart_agri.core.services.advances_service import AdvancesService
        advance = AdvancesService.create_advance(
            employee_id=self.employee.id,
            farm_id=self.farm.id,
            amount="5000",
            date=date(2026, 3, 1),
            reason="سلفة شخصية",
        )
        self.assertEqual(advance.amount, Decimal("5000.0000"))
        self.assertEqual(advance.status, AdvanceStatus.PENDING)

    def test_create_advance_idempotency(self):
        """[Axis 2] Duplicate idempotency_key returns existing."""
        from smart_agri.core.services.advances_service import AdvancesService
        import uuid
        key = uuid.uuid4()
        adv1 = AdvancesService.create_advance(
            employee_id=self.employee.id, farm_id=self.farm.id,
            amount="1000", date=date(2026, 3, 1), idempotency_key=key,
        )
        adv2 = AdvancesService.create_advance(
            employee_id=self.employee.id, farm_id=self.farm.id,
            amount="2000", date=date(2026, 3, 2), idempotency_key=key,
        )
        self.assertEqual(adv1.id, adv2.id)

    def test_create_advance_wrong_farm(self):
        """[Axis 6] Rejects employee from different farm."""
        from smart_agri.core.services.advances_service import AdvancesService
        other = Farm.objects.create(name="Other ADV", slug="other-adv-test")
        with self.assertRaises(ValidationError):
            AdvancesService.create_advance(
                employee_id=self.employee.id, farm_id=other.id,
                amount="1000", date=date(2026, 3, 1),
            )

    def test_create_advance_zero_amount(self):
        """[Axis 5] Rejects zero amount."""
        from smart_agri.core.services.advances_service import AdvancesService
        with self.assertRaises(ValidationError):
            AdvancesService.create_advance(
                employee_id=self.employee.id, farm_id=self.farm.id,
                amount="0", date=date(2026, 3, 1),
            )

    def test_approve_advance(self):
        """[Axis 7] Approve sets status + approved_by."""
        from smart_agri.core.services.advances_service import AdvancesService
        advance = AdvancesService.create_advance(
            employee_id=self.employee.id, farm_id=self.farm.id,
            amount="3000", date=date(2026, 3, 1),
        )
        approved = AdvancesService.approve_advance(advance_id=advance.id, approver=self.user)
        self.assertEqual(approved.status, AdvanceStatus.APPROVED)

    def test_approve_advance_idempotent(self):
        """[Axis 2] Re-approving returns same."""
        from smart_agri.core.services.advances_service import AdvancesService
        adv = EmployeeAdvance.objects.create(
            employee=self.employee, farm=self.farm,
            amount=Decimal("1000.0000"), date=date(2026, 3, 1),
            status=AdvanceStatus.APPROVED, approved_by=self.user,
        )
        result = AdvancesService.approve_advance(advance_id=adv.id, approver=self.user)
        self.assertEqual(result.status, AdvanceStatus.APPROVED)

    def test_deduct_advances_from_payroll(self):
        """[Axis 4/5] Deduction updates slip and advance status."""
        from smart_agri.core.services.advances_service import AdvancesService
        adv = EmployeeAdvance.objects.create(
            employee=self.employee, farm=self.farm,
            amount=Decimal("2000.0000"), date=date(2026, 3, 1),
            status=AdvanceStatus.APPROVED,
        )
        run = PayrollRun.objects.create(
            farm=self.farm, period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31), status=PayrollStatus.DRAFT,
            total_amount=Decimal("0.00"),
        )
        slip = PayrollSlip.objects.create(
            run=run, employee=self.employee,
            basic_amount=Decimal("15000.0000"), net_pay=Decimal("15000.0000"),
            allowances_amount=Decimal("0.0000"), overtime_amount=Decimal("0.0000"),
            deductions_amount=Decimal("0.0000"), days_worked=Decimal("20.0"),
        )
        total = AdvancesService.deduct_advances_from_payroll(
            employee_id=self.employee.id, payroll_slip=slip,
        )
        self.assertEqual(total, Decimal("2000.0000"))
        slip.refresh_from_db()
        self.assertEqual(slip.deductions_amount, Decimal("2000.0000"))
        self.assertEqual(slip.net_pay, Decimal("13000.0000"))
        adv.refresh_from_db()
        self.assertEqual(adv.status, AdvanceStatus.DEDUCTED)

    def test_get_employee_advances(self):
        """[Axis 6] Lists advances for farm."""
        from smart_agri.core.services.advances_service import AdvancesService
        EmployeeAdvance.objects.create(
            employee=self.employee, farm=self.farm,
            amount=Decimal("1000.0000"), date=date(2026, 3, 1),
            status=AdvanceStatus.PENDING,
        )
        results = AdvancesService.get_employee_advances(farm_id=self.farm.id)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'PENDING')


class PayrollServiceTest(TestCase):
    """Tests for PayrollService — Surra normalization, advance integration."""

    @classmethod
    def setUpTestData(cls):
        cls.farm = Farm.objects.create(name="Payroll Farm", slug="payroll-farm-test")
        cls.user = User.objects.create_user(username="pay_user", password="test1234")
        cls.employee = Employee.objects.create(
            farm=cls.farm,
            first_name="خالد",
            last_name="عبدالله",
            employee_id="PAY-001",
            category=EmploymentCategory.CASUAL,
            shift_rate=Decimal("500.0000"),
        )

    def test_normalize_to_quarter(self):
        """Quarter rounding: 0.13→0.25, 0.4→0.50, 0.9→1.00."""
        from smart_agri.core.services.payroll_service import PayrollService
        svc = PayrollService()
        self.assertEqual(svc._normalize_to_quarter(Decimal("0.13")), Decimal("0.25"))
        self.assertEqual(svc._normalize_to_quarter(Decimal("0.40")), Decimal("0.50"))
        self.assertEqual(svc._normalize_to_quarter(Decimal("0.90")), Decimal("1.00"))
        self.assertEqual(svc._normalize_to_quarter(Decimal("0.00")), Decimal("0.00"))
        self.assertEqual(svc._normalize_to_quarter(None), Decimal("0.00"))

    def test_generate_payroll_run(self):
        """Generates draft payroll with correct totals."""
        from smart_agri.core.services.payroll_service import PayrollService
        Timesheet.objects.create(
            employee=self.employee, farm=self.farm,
            date=date(2026, 3, 1), surrah_count=Decimal("1.00"),
            surrah_overtime=Decimal("0.00"),
        )
        run = PayrollService.generate_payroll_run(
            self.farm, date(2026, 3, 1), date(2026, 3, 31), self.user,
        )
        self.assertEqual(run.status, PayrollStatus.DRAFT)
        self.assertTrue(run.total_amount > Decimal("0"))
        self.assertEqual(run.slips.count(), 1)


class WorkerProductivityServiceTest(TestCase):
    """Tests for WorkerProductivityService — KPI output."""

    @classmethod
    def setUpTestData(cls):
        cls.farm = Farm.objects.create(name="KPI Farm", slug="kpi-farm-test")
        cls.employee = Employee.objects.create(
            farm=cls.farm,
            first_name="ياسر",
            last_name="أنور",
            employee_id="KPI-001",
            category=EmploymentCategory.CASUAL,
            shift_rate=Decimal("400.0000"),
        )

    def test_get_labor_kpi(self):
        """Returns structured KPI with summary, workers list, daily trend."""
        from smart_agri.core.services.worker_productivity_service import WorkerProductivityService
        Timesheet.objects.create(
            employee=self.employee, farm=self.farm,
            date=date(2026, 3, 1), surrah_count=Decimal("1.00"),
            surrah_overtime=Decimal("0.00"), is_approved=True,
        )
        result = WorkerProductivityService.get_labor_kpi(farm_id=self.farm.id)
        self.assertIn('summary', result)
        self.assertIn('workers', result)
        self.assertIn('daily_trend', result)
        self.assertEqual(len(result['workers']), 1)
        self.assertEqual(result['summary']['total_entries'], 1)

    def test_get_labor_kpi_no_farm(self):
        """[Axis 6] Returns error if no farm_id."""
        from smart_agri.core.services.worker_productivity_service import WorkerProductivityService
        result = WorkerProductivityService.get_labor_kpi(farm_id=None)
        self.assertIn('error', result)
