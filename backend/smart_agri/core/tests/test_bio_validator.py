from django.test import TestCase
from django.core.exceptions import ValidationError
from smart_agri.core.models import Crop
from smart_agri.core.services.bio_validator import BioValidator

class BioValidatorTest(TestCase):
    def setUp(self):
        self.crop = Crop.objects.create(
            name="Test Mango",
            max_yield_per_tree=50.0, # 50kg/tree
            max_yield_per_ha=10.0, # 10 Tonnes/ha
            phenological_stages={
                 "allowed_actions": {
                     "Harvest": ["Fruiting"],
                     "Prune": ["Vegetative"]
                 }
            }
        )

    def test_impossible_tree_yield(self):
        """Should block 1000kg from 1 tree (Max 50kg)"""
        with self.assertRaises(ValidationError) as cm:
            BioValidator.validate_harvest(self.crop, 1000, tree_count=1)
        self.assertIn("Biological Violation", str(cm.exception))

    def test_possible_tree_yield(self):
        """Should allow 40kg from 1 tree (Max 50kg)"""
        try:
            BioValidator.validate_harvest(self.crop, 40, tree_count=1)
        except ValidationError:
            self.fail("BioValidator raised ValidationError unexpectedly!")

    def test_bumper_season_margin(self):
        """Should allow 10% overage (55kg from 1 tree)"""
        try:
            BioValidator.validate_harvest(self.crop, 55, tree_count=1)
        except ValidationError:
             self.fail("BioValidator failed on allowable margin!")

    def test_phenological_lock(self):
        """Should block Harvest during Vegetative stage"""
        with self.assertRaises(ValidationError):
            BioValidator.validate_activity(self.crop, "Harvest", current_stage="Vegetative")

    def test_phenological_allow(self):
        """Should allow Harvest during Fruiting stage"""
        BioValidator.validate_activity(self.crop, "Harvest", current_stage="Fruiting")
