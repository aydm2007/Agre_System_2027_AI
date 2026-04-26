from decimal import Decimal
import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from smart_agri.core.models.activity import Activity, ActivityHarvest
from smart_agri.core.models.inventory import HarvestLot, Item, Unit
from smart_agri.core.models.farm import Farm, Location
from smart_agri.core.models.crop import Crop, CropProduct
from smart_agri.core.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)

class HarvestQualityService:
    """
    Commercial Logic Layer: Harvest Grading & Quality Control.
    Implements the 'Broken Supply Chain' fix by ensuring harvest data
    is not just a single number, but a graded inventory asset.
    """

    @staticmethod
    @transaction.atomic
    def process_graded_harvest(
        activity: Activity, 
        grades_data: list[dict],
        user
    ):
        """
        Splits a single Harvest Activity into multiple graded Harvest Lots.
        
        grades_data structure:
        [
            {"grade": "Class A", "qty": 1000, "uom": "kg", "product_id": 101},
            {"grade": "Class B", "qty": 200, "uom": "kg", "product_id": 102},
            {"grade": "Waste", "qty": 50, "uom": "kg", "product_id": 103, "is_waste": True}
        ]
        """
        if not activity.task.is_harvest_task:
            raise ValidationError("النشاط المحدد ليس نشاط حصاد.")

        input_weight = None
        if hasattr(activity, "harvest_details") and activity.harvest_details:
            input_weight = activity.harvest_details.harvest_quantity

        if input_weight is None:
            raise ValidationError("يجب تسجيل كمية الحصاد الخام قبل الفرز.")

        normalized_entries = []
        total_output = Decimal("0")
        for entry in grades_data:
            qty = Decimal(str(entry.get("qty", 0)))
            if qty <= 0:
                continue
            normalized_entries.append((entry, qty))
            total_output += qty

        variance = input_weight - total_output
        if abs(variance) > Decimal("0.5"):
            raise ValidationError(
                "اختلال في توازن الكتلة (Mass Balance Mismatch). "
                f"الداخل: {input_weight}، الخارج: {total_output}. "
                f"الفارق: {variance}. يجب تسجيل الفارق كـ 'تالف' أو إعادة الوزن."
            )

        total_qty = Decimal("0")
        
        for entry, qty in normalized_entries:
            grade = entry['grade']
            product_id = entry.get('product_id')
            
            # 1. Validation
            # 2. Resolve Product Item (Inventory Asset)
            try:
                product = CropProduct.objects.get(pk=product_id)
            except CropProduct.DoesNotExist:
                raise ValidationError(f"معرف المنتج {product_id} غير صالح للدرجة {grade}")

            # 3. Create Harvest Lot (Traceable Unit)
            lot = HarvestLot.objects.create(
                farm=activity.log.farm,
                crop=activity.crop,
                crop_plan=activity.crop_plan,
                product=product,
                location=activity.location,
                harvest_date=activity.log.log_date,
                grade=grade,
                quantity=qty,
                uom=entry.get('uom', 'kg'),
                unit=product.item.unit # Link to standard unit
            )

            # 4. Inventory Injection (Single Source of Truth)
            # We record movement for the specific product item (e.g. "Tomato Class A")
            InventoryService.record_movement(
                farm=activity.log.farm,
                item=product.item,
                qty_delta=qty,
                location=activity.location, # Or specific warehouse?
                ref_type="harvest_lot",
                ref_id=str(lot.id),
                note=f"Harvest Grading: {grade}",
                batch_number=entry.get('batch_number') or f"LOT-{lot.id}"
            )

            total_qty += qty

        # 5. Update Activity Aggregate
        # We ensure the parent activity reflects the total sum
        if hasattr(activity, 'harvest_details'):
            activity.harvest_details.harvest_quantity = total_qty
            activity.harvest_details.save()
        else:
             ActivityHarvest.objects.create(
                 activity=activity,
                 harvest_quantity=total_qty,
                 uom=grades_data[0].get('uom', 'kg') if grades_data else 'kg'
             )
        
        return total_qty

    @staticmethod
    def calculate_quality_grade(harvest_log):
        """
        Determines quality based on Supervisor judgment first (Human-in-the-loop).
        Ref: AGRI-GUARDIAN Fix 39 (Platonic Quality Check).
        """
        manual_grade = getattr(harvest_log, 'manual_grade', None)
        if manual_grade:
            return str(manual_grade).strip()

        visual_grade = getattr(harvest_log, 'supervisor_visual_grade', None)
        if visual_grade:
            return str(visual_grade).strip()

        raise ValidationError("يجب إدخال تقييم جودة يدوي من المشرف (بدون حساسات).")
