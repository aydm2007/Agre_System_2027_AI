from django.core.exceptions import ValidationError
from smart_agri.core.models.activity import Activity

class InventoryPolicy:
    """
    طبقة المنطق النقي لقواعد عمل مخزون الأشجار.
    تضمن أن الأنشطة والتعديلات تتوافق مع التوجيهات الزراعية.
    """

    @staticmethod
    def is_tree_tracked(activity: Activity) -> bool:
        """تحديد ما إذا كان النشاط يجب أن يؤثر على مخزون الأشجار."""
        crop = activity.crop
        task = activity.task
        if not crop or not task:
            return False
        
        # قاعدة: الإجراءات المعمرة أو متطلبات عدد الأشجار الصريحة
        is_procedural = getattr(task, "is_perennial_procedure", False) or \
                        getattr(task, "requires_tree_count", False)
        
        loc = activity.activity_locations.first()
        return bool(is_procedural and loc and loc.location and activity.variety)

    @staticmethod
    def validate_activity_for_stock(activity: Activity) -> None:
        """التحقق من أن النشاط يحتوي على جميع البيانات اللازمة لتغيير المخزون."""
        errors = {}
        
        loc = activity.activity_locations.first()
        if not loc or not loc.location:
            errors["location"] = "يجب تحديد الموقع لتحديث مخزون الأشجار."
        if not activity.variety:
            errors["variety"] = "يجب تحديد الصنف لتحديث مخزون الأشجار."
            
        # قاعدة: الفقد يتطلب سبباً
        if (activity.tree_count_delta or 0) < 0 and not activity.tree_loss_reason:
            errors["tree_loss_reason"] = "سبب الفقد مطلوب عند تسجيل نقص في عدد الأشجار."
            
        # قاعدة: الحصاد يتطلب كمية
        if activity.task and activity.task.is_harvest_task:
            harvest_qty = getattr(activity, "harvest_quantity", None)
            harvest_ext = getattr(activity, "harvest_details", None)
            if harvest_qty is None and (harvest_ext is None or harvest_ext.harvest_quantity is None):
                errors["harvest_quantity"] = "كمية الحصاد مطلوبة لمهام الحصاد."
        
        if errors:
            raise ValidationError(errors)

    @staticmethod
    def validate_manual_adjustment(resulting_count, delta, reason) -> None:
        """التحقق من صحة مدخلات تعديل المخزون اليدوي."""
        if not (reason or "").strip():
             raise ValidationError({"reason": "السبب مطلوب للتعديلات اليدوية."})
             
        if resulting_count is None and delta is None:
            raise ValidationError({"resulting_tree_count": "يجب تحديد إما الرصيد النهائي أو التغيير في العدد."})
        
        if resulting_count is not None and delta is not None:
             raise ValidationError({"delta": "حدد إما الرصيد النهائي أو التغيير في العدد، وليس كلاهما."})
             
        if resulting_count is not None and resulting_count < 0:
            raise ValidationError({"resulting_tree_count": "العدد الناتج لا يمكن أن يكون سالباً."})
