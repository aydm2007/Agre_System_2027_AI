"""
[AGRI-GUARDIAN] Test Suite: Fiscal Period Lifecycle
Target: FiscalPeriod model
Protocol: Three-stage state machine: open → soft_close → hard_close
          - hard_close is IRREVERSIBLE
"""
import pytest
from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from smart_agri.finance.models import FiscalYear, FiscalPeriod
from smart_agri.core.models.farm import Farm


@pytest.mark.django_db
class TestFiscalPeriodLifecycle(TestCase):
    """
    التحقق من دورة حياة الفترة المالية وفقاً لبروتوكول Agri-Guardian:
    فتح ← إغلاق مبدئي ← إغلاق نهائي (لا رجعة).
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="fiscal_admin",
            email="admin@example.com",
            password="pass1234",
        )
        # Farm model has: name, slug, region (no owner_id)
        self.farm = Farm.objects.create(
            name="Fiscal Test Farm",
            slug="fiscal-test-farm",
            region="Test Region",
        )
        self.fiscal_year = FiscalYear.objects.create(
            farm=self.farm,
            year=2026,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.period = FiscalPeriod.objects.create(
            fiscal_year=self.fiscal_year,
            month=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            status=FiscalPeriod.STATUS_OPEN,
        )

    def test_initial_status_is_open(self):
        """
        اختبار: الفترة الجديدة تبدأ بحالة 'open'.
        """
        self.assertEqual(self.period.status, FiscalPeriod.STATUS_OPEN)

    def test_soft_close_from_open(self):
        """
        اختبار: الانتقال من 'open' إلى 'soft_close' ينجح.
        """
        self.period.status = FiscalPeriod.STATUS_SOFT_CLOSE
        self.period.save()
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, FiscalPeriod.STATUS_SOFT_CLOSE)

    def test_hard_close_from_soft_close(self):
        """
        اختبار: الانتقال من 'soft_close' إلى 'hard_close' ينجح.
        """
        self.period.status = FiscalPeriod.STATUS_SOFT_CLOSE
        self.period.save()
        self.period.status = FiscalPeriod.STATUS_HARD_CLOSE
        self.period.save()
        self.period.refresh_from_db()
        self.assertEqual(self.period.status, FiscalPeriod.STATUS_HARD_CLOSE)

    def test_reopen_hard_closed_fails(self):
        """
        اختبار: محاولة إعادة فتح فترة مغلقة نهائياً تفشل.
        الإغلاق النهائي لا رجعة فيه.
        """
        self.period.status = FiscalPeriod.STATUS_SOFT_CLOSE
        self.period.save()
        self.period.status = FiscalPeriod.STATUS_HARD_CLOSE
        self.period.save()
        self.period.refresh_from_db()

        self.period.status = FiscalPeriod.STATUS_OPEN
        with self.assertRaises(ValidationError):
            self.period.clean()

    def test_unique_month_per_fiscal_year(self):
        """
        اختبار: لا يمكن إنشاء فترتين بنفس الشهر في نفس السنة المالية.
        """
        from django.db import IntegrityError, transaction as db_transaction
        with self.assertRaises(IntegrityError):
            with db_transaction.atomic():
                FiscalPeriod.objects.create(
                    fiscal_year=self.fiscal_year,
                    month=1,  # Same month as setUp
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 1, 31),
                    status=FiscalPeriod.STATUS_OPEN,
                )
