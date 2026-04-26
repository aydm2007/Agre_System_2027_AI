from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models.activity import Activity
from smart_agri.core.models.crop import Crop
from smart_agri.core.models.farm import Farm, Location
from smart_agri.core.models.log import DailyLog
from smart_agri.core.models.planning import CropPlan
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.log_approval_service import LogApprovalService
from smart_agri.core.services.smart_card_stack_service import (
    build_smart_card_stack,
    resolve_card_visibility,
)

User = get_user_model()


class SimpleModeCropVarianceAuditTests(TestCase):
    """
    SIMPLE-mode audit for crop plans, smart-card outputs, and approved variance
    evidence across seasonal and perennial crops.
    """

    def setUp(self):
        self.operator = User.objects.create_user(username="simple_audit_operator", password="password")
        self.manager = User.objects.create_user(username="simple_audit_manager", password="password")

        self.farm = Farm.objects.create(name="مزرعة التدقيق المبسط", slug="simple-audit-farm", tier="MEDIUM")
        self.settings = FarmSettings.objects.create(farm=self.farm, mode=FarmSettings.MODE_SIMPLE)

        FarmMembership.objects.create(user=self.operator, farm=self.farm, role="مشرف ميداني")
        FarmMembership.objects.create(user=self.manager, farm=self.farm, role="مدير المزرعة")

        self.locations = {
            "wheat": Location.objects.create(farm=self.farm, name="حقل القمح", code="AUD-WHEAT"),
            "mango": Location.objects.create(farm=self.farm, name="بستان المانجو", code="AUD-MANGO"),
            "banana": Location.objects.create(farm=self.farm, name="بستان الموز", code="AUD-BANANA"),
        }

        self.crops = {
            "wheat": Crop.objects.create(name="قمح", is_perennial=False),
            "mango": Crop.objects.create(name="مانجو", is_perennial=True),
            "banana": Crop.objects.create(name="موز", is_perennial=True),
        }

        self.plans = {
            "wheat": CropPlan.objects.create(
                farm=self.farm,
                crop=self.crops["wheat"],
                name="خطة القمح الربيعية 2026",
                status="ACTIVE",
                start_date=timezone.localdate(),
                end_date=timezone.localdate() + timedelta(days=120),
                area=Decimal("15.0"),
            ),
            "mango": CropPlan.objects.create(
                farm=self.farm,
                crop=self.crops["mango"],
                name="خطة خدمة المانجو 2026",
                status="ACTIVE",
                start_date=timezone.localdate(),
                end_date=timezone.localdate() + timedelta(days=180),
                area=Decimal("8.0"),
            ),
            "banana": CropPlan.objects.create(
                farm=self.farm,
                crop=self.crops["banana"],
                name="خطة خدمة الموز 2026",
                status="ACTIVE",
                start_date=timezone.localdate(),
                end_date=timezone.localdate() + timedelta(days=180),
                area=Decimal("6.0"),
            ),
        }

    def _task_contract(self, *, perennial):
        smart_cards = {
            "execution": {"enabled": True},
            "materials": {"enabled": True},
            "labor": {"enabled": True},
            "control": {"enabled": True},
            "variance": {"enabled": True},
            "perennial": {"enabled": perennial},
        }
        return {
            "smart_cards": smart_cards,
            "presentation": {
                "card_order": [
                    "execution",
                    "materials",
                    "labor",
                    "perennial",
                    "control",
                    "variance",
                ]
            },
            "control_rules": {
                "mode": "SIMPLE",
                "variance_requires_manager": True,
            },
        }

    def _create_log_and_activity(self, key, *, date_offset_days):
        crop_plan = self.plans[key]
        log = DailyLog.objects.create(
            farm=self.farm,
            log_date=timezone.localdate() + timedelta(days=date_offset_days),
            created_by=self.operator,
            status=DailyLog.STATUS_SUBMITTED,
            notes=f"سجل تدقيق مبسط للمحصول {crop_plan.crop.name}",
        )
        activity = Activity.objects.create(
            log=log,
            crop_plan=crop_plan,
            crop=crop_plan.crop,
            location=self.locations[key],
            created_by=self.operator,
            days_spent=Decimal("1.0"),
            cost_total=Decimal("1250.00"),
            task_contract_snapshot=self._task_contract(perennial=crop_plan.crop.is_perennial),
        )
        return log, activity

    def test_simple_mode_crop_plans_emit_canonical_technical_and_control_outputs(self):
        wheat_log, wheat_activity = self._create_log_and_activity("wheat", date_offset_days=0)
        mango_log, mango_activity = self._create_log_and_activity("mango", date_offset_days=-1)
        banana_log, banana_activity = self._create_log_and_activity("banana", date_offset_days=-2)

        self.assertEqual(self.settings.visibility_level, "operations_only")
        self.assertEqual(wheat_activity.crop_plan_id, self.plans["wheat"].id)
        self.assertEqual(mango_activity.crop_plan_id, self.plans["mango"].id)
        self.assertEqual(banana_activity.crop_plan_id, self.plans["banana"].id)

        wheat_stack = build_smart_card_stack(wheat_activity)
        mango_stack = build_smart_card_stack(mango_activity)
        banana_stack = build_smart_card_stack(banana_activity)

        wheat_keys = {card["card_key"] for card in wheat_stack}
        mango_keys = {card["card_key"] for card in mango_stack}
        banana_keys = {card["card_key"] for card in banana_stack}

        self.assertSetEqual(
            wheat_keys,
            {"execution", "materials", "labor", "control", "variance"},
        )
        self.assertSetEqual(
            mango_keys,
            {"execution", "materials", "labor", "perennial", "control", "variance"},
        )
        self.assertSetEqual(
            banana_keys,
            {"execution", "materials", "labor", "perennial", "control", "variance"},
        )

        for card in wheat_stack + mango_stack + banana_stack:
            self.assertTrue(resolve_card_visibility(card, self.settings))
            self.assertNotEqual(card["card_key"], "financial_trace")

        self.assertEqual(wheat_log.status, DailyLog.STATUS_SUBMITTED)
        self.assertEqual(mango_log.status, DailyLog.STATUS_SUBMITTED)
        self.assertEqual(banana_log.status, DailyLog.STATUS_SUBMITTED)

    @patch(
        "smart_agri.core.services.log_approval_service.compute_log_variance",
        return_value={
            "status": "CRITICAL",
            "max_deviation_pct": Decimal("28.00"),
            "details": [
                {
                    "axis": "perennial",
                    "note": "انحراف حرج يحتاج اعتماد المدير.",
                }
            ],
        },
    )
    def test_manager_can_approve_mango_and_banana_critical_variances_in_simple(self, variance_mock):
        mango_log, _ = self._create_log_and_activity("mango", date_offset_days=-1)
        banana_log, _ = self._create_log_and_activity("banana", date_offset_days=-2)

        LogApprovalService.approve_variance(self.manager, mango_log.id, note="تم اعتماد انحراف المانجو بعد المراجعة.")
        LogApprovalService.approve_variance(self.manager, banana_log.id, note="تم اعتماد انحراف الموز بعد المراجعة.")

        mango_log.refresh_from_db()
        banana_log.refresh_from_db()

        self.assertEqual(mango_log.variance_status, "CRITICAL")
        self.assertEqual(banana_log.variance_status, "CRITICAL")
        self.assertEqual(mango_log.variance_approved_by_id, self.manager.id)
        self.assertEqual(banana_log.variance_approved_by_id, self.manager.id)
        self.assertEqual(mango_log.variance_note, "تم اعتماد انحراف المانجو بعد المراجعة.")
        self.assertEqual(banana_log.variance_note, "تم اعتماد انحراف الموز بعد المراجعة.")
        self.assertIsNotNone(mango_log.variance_approved_at)
        self.assertIsNotNone(banana_log.variance_approved_at)
        self.assertGreaterEqual(variance_mock.call_count, 2)
