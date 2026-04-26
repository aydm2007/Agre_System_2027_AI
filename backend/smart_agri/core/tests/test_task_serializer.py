from django.test import TestCase

from smart_agri.core.api.serializers.task import TaskSerializer
from smart_agri.core.models import Crop, Farm, Task


class TaskSerializerTests(TestCase):
    def setUp(self):
        self.farm = Farm.objects.create(name="مزرعة تجريبية", slug="farm-task-serializer", region="north")
        self.crop = Crop.objects.create(name="مانجو", mode="Open")
        self.crop.farm_links.create(farm=self.farm)

    def _payload(self, **overrides):
        payload = {
            "crop": self.crop.id,
            "stage": "خدمة",
            "name": "مهمة ذكية",
            "archetype": Task.Archetype.GENERAL,
        }
        payload.update(overrides)
        return payload

    def test_explicit_task_contract_derives_perennial_flags(self):
        serializer = TaskSerializer(
            data=self._payload(
                task_contract={
                    "smart_cards": {
                        "execution": {"enabled": True},
                        "materials": {"enabled": True},
                        "perennial": {"enabled": True},
                        "control": {"enabled": True},
                        "variance": {"enabled": True},
                    }
                }
            )
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertTrue(serializer.validated_data["requires_tree_count"])
        self.assertTrue(serializer.validated_data["is_perennial_procedure"])

    def test_fuel_card_requires_machinery(self):
        serializer = TaskSerializer(
            data=self._payload(
                task_contract={
                    "smart_cards": {
                        "execution": {"enabled": True},
                        "fuel": {"enabled": True},
                        "control": {"enabled": True},
                        "variance": {"enabled": True},
                    }
                }
            )
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertTrue(serializer.validated_data["requires_machinery"])

    def test_mandatory_cards_cannot_be_disabled(self):
        serializer = TaskSerializer(
            data=self._payload(
                task_contract={
                    "smart_cards": {
                        "execution": {"enabled": False},
                        "control": {"enabled": True},
                        "variance": {"enabled": True},
                    }
                }
            )
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("task_contract", serializer.errors)

    def test_effective_task_contract_reflects_explicit_overrides(self):
        serializer = TaskSerializer(
            data=self._payload(
                archetype=Task.Archetype.PERENNIAL_SERVICE,
                task_contract={
                    "smart_cards": {
                        "execution": {"enabled": True},
                        "materials": {"enabled": True},
                        "labor": {"enabled": True},
                        "perennial": {"enabled": True},
                        "control": {"enabled": True},
                        "variance": {"enabled": True},
                        "financial_trace": {"enabled": True},
                    },
                    "presentation": {
                        "simple_preview": ["execution", "materials", "labor", "perennial", "control", "variance"],
                        "strict_preview": [
                            "execution",
                            "materials",
                            "labor",
                            "perennial",
                            "control",
                            "variance",
                            "financial_trace",
                        ],
                    },
                },
            )
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        task = serializer.save()
        effective = task.get_effective_contract()
        self.assertTrue(effective["smart_cards"]["materials"]["enabled"])
        self.assertEqual(
            effective["presentation"]["simple_preview"],
            ["execution", "materials", "labor", "perennial", "control", "variance"],
        )
