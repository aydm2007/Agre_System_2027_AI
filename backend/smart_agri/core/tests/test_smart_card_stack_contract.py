from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from smart_agri.core.models import Crop, Task, Activity, DailyLog, Farm
from smart_agri.core.models.settings import FarmSettings
from smart_agri.core.services.smart_card_stack_service import (
    build_smart_card_stack,
    resolve_card_visibility,
    scrub_disabled_cards,
)

class TestSmartCardStackContract(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.farm = Farm.objects.create(name="Test Farm")
        cls.farm_settings = FarmSettings.objects.create(
            farm=cls.farm, mode="SIMPLE", show_daily_log_smart_card=True
        )
        cls.crop = Crop.objects.create(name="Test Crop", mode="Open")
        cls.log = DailyLog.objects.create(farm=cls.farm, log_date=timezone.localdate())
        
        # Create a task and save it to build and persist its default contract
        cls.task = Task.objects.create(crop=cls.crop, name="Test Task", stage="General")
        cls.task.save()
        
        # Override contract for test predictability
        cls.task.task_contract = {
            "smart_cards": {
                "execution": {"enabled": True},
                "materials": {"enabled": True},
                "labor": {"enabled": False}, # Disabled for test
                "financial_trace": {"enabled": True},
            },
            "presentation": {
                "card_order": ["execution", "materials", "labor", "financial_trace"]
            }
        }
        cls.task.save()

    def test_stack_from_task_contract_snapshot(self):
        # Build activity with a distinct snapshot
        snapshot = {
            "smart_cards": {
                "execution": {"enabled": True},
                "variance": {"enabled": True},
            },
            "presentation": {"card_order": ["execution", "variance"]}
        }
        activity = Activity.objects.create(
            log=self.log, task=self.task, task_contract_snapshot=snapshot
        )
        
        stack = build_smart_card_stack(activity)
        self.assertEqual(len(stack), 2)
        keys = [card["card_key"] for card in stack]
        self.assertIn("execution", keys)
        self.assertIn("variance", keys)

    def test_stack_fallback_to_live_contract(self):
        # Build activity with empty snapshot, it should fall back to task.task_contract
        activity = Activity.objects.create(
            log=self.log, task=self.task, task_contract_snapshot={}
        )
        
        stack = build_smart_card_stack(activity)
        self.assertEqual(len(stack), 3) # execution, materials, financial_trace
        keys = [card["card_key"] for card in stack]
        self.assertIn("execution", keys)
        self.assertIn("materials", keys)
        self.assertIn("financial_trace", keys)
        self.assertNotIn("labor", keys) # Labor was explicitly false in the live contract

    def test_card_has_all_required_fields(self):
        activity = Activity.objects.create(
            log=self.log, task=self.task, task_contract_snapshot={}
        )
        stack = build_smart_card_stack(activity)
        self.assertTrue(len(stack) > 0)
        
        expected_fields = [
            "card_key", "title", "enabled", "order", "mode_visibility",
            "status", "metrics", "flags", "data_source", "policy", "source_refs"
        ]
        
        for card in stack:
            for field in expected_fields:
                self.assertIn(field, card)

    def test_disabled_cards_scrubbed(self):
        activity = Activity.objects.create(
            log=self.log, task=self.task, task_contract_snapshot={}
        )
        stack = build_smart_card_stack(activity)
        # Manually force a disabled card into the stack to test the scrubber
        stack.append({"card_key": "labor", "enabled": False})
        
        scrubbed = scrub_disabled_cards(stack, self.task.task_contract)
        
        for card in scrubbed:
            self.assertNotEqual(card["card_key"], "labor")

    def test_simple_mode_hides_finance_cards(self):
        activity = Activity.objects.create(
            log=self.log, task=self.task, task_contract_snapshot={}
        )
        stack = build_smart_card_stack(activity)
        
        # Enforce strict_only logic
        self.farm_settings.mode = "SIMPLE"
        self.farm_settings.save()
        
        visible_stack = [c for c in stack if resolve_card_visibility(c, self.farm_settings)]
        
        keys = [c["card_key"] for c in visible_stack]
        self.assertIn("execution", keys)
        self.assertNotIn("financial_trace", keys) # Hidden by SIMPLE mode
        
        # Toggle to STRICT
        self.farm_settings.mode = "STRICT"
        self.farm_settings.save()
        
        visible_stack_strict = [c for c in stack if resolve_card_visibility(c, self.farm_settings)]
        keys_strict = [c["card_key"] for c in visible_stack_strict]
        self.assertIn("financial_trace", keys_strict)

    def test_show_daily_log_smart_card_toggle(self):
        activity = Activity.objects.create(log=self.log, task=self.task)
        stack = build_smart_card_stack(activity)
        
        # Enabled by default
        self.assertTrue(any(resolve_card_visibility(c, self.farm_settings) for c in stack))
        
        # Disabled globally via FarmSettings
        self.farm_settings.show_daily_log_smart_card = False
        self.farm_settings.save()
        
        # No cards should be visible
        visible_stack = [c for c in stack if resolve_card_visibility(c, self.farm_settings)]
        self.assertEqual(len(visible_stack), 0)
