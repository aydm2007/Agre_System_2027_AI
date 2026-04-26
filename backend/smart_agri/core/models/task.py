from copy import deepcopy
from django.db import models

from .base import SoftDeleteModel
from .crop import Crop


class Task(SoftDeleteModel):
    class Archetype(models.TextChoices):
        GENERAL = "GENERAL", "General"
        IRRIGATION = "IRRIGATION", "Irrigation"
        MACHINERY = "MACHINERY", "Machinery"
        HARVEST = "HARVEST", "Harvest"
        PERENNIAL_SERVICE = "PERENNIAL_SERVICE", "Perennial Service"
        LABOR_INTENSIVE = "LABOR_INTENSIVE", "Labor Intensive"
        MATERIAL_INTENSIVE = "MATERIAL_INTENSIVE", "Material Intensive"
        FUEL_SENSITIVE = "FUEL_SENSITIVE", "Fuel Sensitive"
        BIOLOGICAL_ADJUSTMENT = "BIOLOGICAL_ADJUSTMENT", "Biological Adjustment"
        CONTRACT_SETTLEMENT_LINKED = "CONTRACT_SETTLEMENT_LINKED", "Contract Settlement Linked"

    class AssetType(models.TextChoices):
        TREE = "TREE", "Trees"
        WELL = "WELL", "Wells"
        MACHINE = "MACHINE", "Machines"
        SECTOR = "SECTOR", "Sectors"
        NONE = "NONE", "General"

    def __init__(self, *args, **kwargs):
        # Avoid injecting kwargs during ORM row hydration (positional args path).
        if not args and "stage" not in kwargs:
            kwargs["stage"] = "General"
        super().__init__(*args, **kwargs)

    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name="tasks")
    stage = models.CharField(max_length=60)
    name = models.CharField(max_length=150)
    requires_area = models.BooleanField(default=False)
    requires_machinery = models.BooleanField(default=False)
    requires_well = models.BooleanField(default=False)
    is_harvest_task = models.BooleanField(default=False)
    requires_tree_count = models.BooleanField(default=False)
    is_perennial_procedure = models.BooleanField(default=False)
    is_asset_task = models.BooleanField(default=False)
    archetype = models.CharField(
        max_length=40,
        choices=Archetype.choices,
        default=Archetype.GENERAL,
    )
    asset_type = models.CharField(max_length=50, null=True, blank=True)
    target_asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
        default=AssetType.NONE,
        help_text="Target asset type for filtering.",
    )
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    task_contract = models.JSONField(default=dict, blank=True)
    task_contract_version = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "مهمة"
        verbose_name_plural = "المهام"

    @staticmethod
    def _default_card_toggle(enabled):
        return {"enabled": bool(enabled)}

    def build_default_contract(self):
        machinery_enabled = bool(self.requires_machinery or self.is_asset_task)
        well_enabled = bool(self.requires_well)
        perennial_enabled = bool(self.requires_tree_count or self.is_perennial_procedure)
        harvest_enabled = bool(self.is_harvest_task)
        material_enabled = self.archetype in {
            self.Archetype.MATERIAL_INTENSIVE,
            self.Archetype.HARVEST,
        }
        labor_enabled = self.archetype in {
            self.Archetype.LABOR_INTENSIVE,
            self.Archetype.PERENNIAL_SERVICE,
        }
        fuel_enabled = self.archetype in {
            self.Archetype.FUEL_SENSITIVE,
            self.Archetype.MACHINERY,
        } or machinery_enabled

        return {
            "input_profile": {
                "requires_well": bool(self.requires_well),
                "requires_machinery": bool(self.requires_machinery),
                "requires_area": bool(self.requires_area),
                "requires_tree_count": bool(self.requires_tree_count),
                "is_harvest_task": bool(self.is_harvest_task),
                "is_perennial_procedure": bool(self.is_perennial_procedure),
                "requires_materials": bool(material_enabled),
                "requires_labor_batch": bool(labor_enabled),
                "requires_service_rows": bool(perennial_enabled or material_enabled),
                "asset_type": self.asset_type or "",
                "target_asset_type": self.target_asset_type,
            },
            "smart_cards": {
                "execution": self._default_card_toggle(True),
                "materials": self._default_card_toggle(material_enabled),
                "labor": self._default_card_toggle(labor_enabled),
                "well": self._default_card_toggle(well_enabled),
                "machinery": self._default_card_toggle(machinery_enabled),
                "fuel": self._default_card_toggle(fuel_enabled),
                "perennial": self._default_card_toggle(perennial_enabled),
                "harvest": self._default_card_toggle(harvest_enabled),
                "control": self._default_card_toggle(True),
                "variance": self._default_card_toggle(True),
                "financial_trace": self._default_card_toggle(True),
            },
            "control_rules": {
                "approval_posture": "basic" if self.archetype == self.Archetype.GENERAL else "tiered",
                "criticality": "high" if harvest_enabled or perennial_enabled else "normal",
                "mandatory_readings": {
                    "well_reading": bool(well_enabled),
                    "machine_hours": bool(machinery_enabled),
                    "tree_count": bool(perennial_enabled),
                },
            },
            "variance_rules": {
                "behavior": "warn",
                "categories": {
                    "cost": True,
                    "quantity": bool(material_enabled or harvest_enabled),
                    "time": True,
                    "water": bool(well_enabled),
                    "fuel": bool(fuel_enabled),
                    "tree_loss": bool(perennial_enabled),
                    "harvest_gap": bool(harvest_enabled),
                },
                "thresholds": {
                    "warning_pct": 10,
                    "critical_pct": 20,
                },
            },
            "financial_profile": {
                "shadow_mode": "shadow_only" if self.archetype == self.Archetype.GENERAL else "shadow_and_trace",
                "wip_impact": bool(material_enabled or labor_enabled or machinery_enabled),
                "petty_cash_relevant": bool(labor_enabled),
                "inventory_linked": bool(material_enabled or harvest_enabled or fuel_enabled),
                "settlement_linked": bool(harvest_enabled or self.archetype == self.Archetype.CONTRACT_SETTLEMENT_LINKED),
                "biological_asset_linked": bool(perennial_enabled),
            },
            "presentation": {
                "simple_preview": [
                    "execution",
                    *([ "well" ] if well_enabled else []),
                    *([ "machinery" ] if machinery_enabled else []),
                    *([ "materials" ] if material_enabled else []),
                    *([ "labor" ] if labor_enabled else []),
                    *([ "perennial" ] if perennial_enabled else []),
                    *([ "harvest" ] if harvest_enabled else []),
                    "control",
                    "variance",
                ],
                "strict_preview": [
                    "execution",
                    *([ "well" ] if well_enabled else []),
                    *([ "machinery" ] if machinery_enabled else []),
                    *([ "fuel" ] if fuel_enabled else []),
                    *([ "materials" ] if material_enabled else []),
                    *([ "labor" ] if labor_enabled else []),
                    *([ "perennial" ] if perennial_enabled else []),
                    *([ "harvest" ] if harvest_enabled else []),
                    "control",
                    "variance",
                    "financial_trace",
                ],
                "card_order": [
                    "execution",
                    "materials",
                    "labor",
                    "well",
                    "machinery",
                    "fuel",
                    "perennial",
                    "harvest",
                    "control",
                    "variance",
                    "financial_trace",
                ],
            },
        }

    def get_effective_contract(self):
        default_contract = self.build_default_contract()
        merged = deepcopy(default_contract)
        current = self.task_contract or {}
        for section, payload in current.items():
            if isinstance(payload, dict) and isinstance(merged.get(section), dict):
                merged[section].update(payload)
            else:
                merged[section] = payload
        return merged

    def save(self, *args, **kwargs):
        if not self.crop_id:
            crop, _ = Crop.objects.get_or_create(name="Legacy Crop", mode="Open")
            self.crop = crop
        if not self.stage:
            self.stage = "General"
        if not self.task_contract:
            self.task_contract = self.build_default_contract()
            if not self.task_contract_version:
                self.task_contract_version = 1
        elif self.pk:
            previous = Task.objects.filter(pk=self.pk).values(
                "task_contract",
                "archetype",
                "requires_area",
                "requires_machinery",
                "requires_well",
                "is_harvest_task",
                "requires_tree_count",
                "is_perennial_procedure",
                "is_asset_task",
                "asset_type",
                "target_asset_type",
            ).first()
            if previous:
                previous_fingerprint = {
                    key: previous[key]
                    for key in previous
                }
                current_fingerprint = {
                    "task_contract": self.task_contract,
                    "archetype": self.archetype,
                    "requires_area": self.requires_area,
                    "requires_machinery": self.requires_machinery,
                    "requires_well": self.requires_well,
                    "is_harvest_task": self.is_harvest_task,
                    "requires_tree_count": self.requires_tree_count,
                    "is_perennial_procedure": self.is_perennial_procedure,
                    "is_asset_task": self.is_asset_task,
                    "asset_type": self.asset_type,
                    "target_asset_type": self.target_asset_type,
                }
                if previous_fingerprint != current_fingerprint:
                    self.task_contract_version = (self.task_contract_version or 1) + 1
        elif not self.task_contract_version:
            self.task_contract_version = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.crop} / {self.stage} / {self.name}"
