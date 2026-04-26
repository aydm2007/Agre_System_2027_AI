from abc import ABC, abstractmethod
from decimal import Decimal
from smart_agri.core.models.activity import (
    ActivityHarvest, ActivityIrrigation, 
    ActivityMaterialApplication, ActivityMachineUsage,
    ActivityPlanting
)
from smart_agri.core.signals import harvest_confirmed
from smart_agri.core.services.bio_validator import BioValidator
from smart_agri.core.models.tree import LocationTreeStock
from django.db.models import Sum

class AbstractExtensionHandler(ABC):
    @abstractmethod
    def handle(self, activity, data: dict):
        pass
    
    @abstractmethod
    def can_handle(self, activity, data: dict) -> bool:
        pass

class HarvestHandler(AbstractExtensionHandler):
    def can_handle(self, activity, data: dict) -> bool:
        return bool(activity.task and activity.task.is_harvest_task)

    def handle(self, activity, data: dict):
        harvest_defaults = {
            'harvest_quantity': data.get('harvest_quantity'),
            'uom': data.get('harvest_uom') or data.get('uom') or 'kg',
            'product_id': data.get('product_id'),
            'batch_number': data.get('batch_number') or ''
        }
        # clean up Nones in case partial update
        harvest_defaults = {k: v for k, v in harvest_defaults.items() if v is not None}
        ActivityHarvest.objects.update_or_create(
            activity=activity, 
            defaults=harvest_defaults
        )
        # [Protocol XVIII] Bio-Constraint Enforcement
        if data.get('harvest_quantity') and activity.crop_plan:
             quantity = Decimal(str(data.get('harvest_quantity')))
             crop = activity.crop_plan.crop
             
             # 1. Fetch Context
             tree_count = LocationTreeStock.objects.filter(
                 location=activity.location, 
                 crop_variety__crop=crop 
             ).aggregate(total=Sum('current_tree_count'))['total'] or 0
             
             hectare_count = activity.crop_plan.area or 0
             
             # 2. Validate
             BioValidator.validate_harvest(
                 crop=crop, 
                 quantity_kg=quantity, 
                 tree_count=int(tree_count), 
                 hectare_count=Decimal(str(hectare_count))
             )

             # Signal
             harvest_confirmed.send(
                 sender=ActivityHarvest,
                 activity=activity,
                 quantity=data.get('harvest_quantity'),
                 batch_number=data.get('batch_number'),
                 user=activity.created_by
             )

class IrrigationHandler(AbstractExtensionHandler):
    def can_handle(self, activity, data: dict) -> bool:
        return (data.get('water_volume') is not None or 
                data.get('well_reading') is not None or 
                data.get('is_solar_powered') is not None)

    def handle(self, activity, data: dict):
        raw_solar = data.get('is_solar_powered')
        is_solar = False
        if raw_solar is not None:
            if isinstance(raw_solar, str):
                is_solar = raw_solar.lower() in ('true', '1', 't', 'y', 'yes')
            else:
                is_solar = bool(raw_solar)
        
        water_volume = data.get('water_volume')
        well_reading = data.get('well_reading')
        diesel_qty = data.get('diesel_qty') if not is_solar else None
        
        ActivityIrrigation.objects.update_or_create(
            activity=activity,
            defaults={
                'water_volume': water_volume if water_volume not in ["", None] else Decimal("0"),
                'uom': data.get('water_uom') or 'm3',
                'well_reading': well_reading if well_reading not in ["", None] else None,
                'well_asset_id': data.get('well_asset_id') or data.get('well_id'),
                'is_solar_powered': is_solar,
                'diesel_qty': diesel_qty if diesel_qty not in ["", None] else None
            }
        )
        # Bio-Validation
        activity.refresh_from_db()
        BioValidator.validate_irrigation(activity)

class MachineUsageHandler(AbstractExtensionHandler):
    def can_handle(self, activity, data: dict) -> bool:
        return data.get('machine_hours') is not None or data.get('fuel_consumed') is not None

    def handle(self, activity, data: dict):
        machine_hours = data.get('machine_hours')
        fuel_consumed = data.get('fuel_consumed')
        start_meter = data.get('start_meter')
        end_meter = data.get('end_meter')
        
        ActivityMachineUsage.objects.update_or_create(
            activity=activity,
            defaults={
                'machine_hours': machine_hours if machine_hours not in ["", None] else Decimal("0"),
                'fuel_consumed': fuel_consumed if fuel_consumed not in ["", None] else None,
                'start_meter': start_meter if start_meter not in ["", None] else None,
                'end_meter': end_meter if end_meter not in ["", None] else None,
            }
        )

class MaterialApplicationHandler(AbstractExtensionHandler):
    def can_handle(self, activity, data: dict) -> bool:
        return data.get('fertilizer_quantity') is not None

    def handle(self, activity, data: dict):
        fertilizer_quantity = data.get('fertilizer_quantity')
        ActivityMaterialApplication.objects.update_or_create(
            activity=activity,
            defaults={
                'fertilizer_quantity': fertilizer_quantity if fertilizer_quantity not in ["", None] else None
            }
        )

class PlantingHandler(AbstractExtensionHandler):
    def can_handle(self, activity, data: dict) -> bool:
        return data.get('planted_area') is not None

    def handle(self, activity, data: dict):
        planted_area = data.get('planted_area')
        planted_area_m2 = data.get('planted_area_m2')
        ActivityPlanting.objects.update_or_create(
            activity=activity,
            defaults={
                'planted_area': planted_area if planted_area not in ["", None] else None,
                'planted_uom': data.get('planted_uom'),
                'planted_area_m2': planted_area_m2 if planted_area_m2 not in ["", None] else None,
            }
        )

# Registry / Processor
class ExtensionProcessor:
    def __init__(self):
        self.handlers: list[AbstractExtensionHandler] = [
            HarvestHandler(),
            IrrigationHandler(),
            MachineUsageHandler(),
            MaterialApplicationHandler(),
            PlantingHandler()
        ]

    def process_extensions(self, activity, data: dict):
        for handler in self.handlers:
            if handler.can_handle(activity, data):
                handler.handle(activity, data)
