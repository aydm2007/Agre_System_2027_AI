import uuid
from django.utils import timezone

class TraceabilityService:
    """
    خدمة مسؤولة عن توليد أكواد التتبع وربط المدخلات بالمخرجات.
    المعيار: GS1-Like Traceability
    """

    @staticmethod
    def generate_batch_number(farm_code, crop_code, date=None):
        """
        توليد رقم تشغيلة فريد بالصيغة:
        [رمز المزرعة]-[رمز المحصول]-[التاريخ]-[معرف فريد]
        مثال: FARM01-MANGO-20260127-A1B2
        """
        if not date:
            date = timezone.now()
        
        # تنظيف الرموز لضمان أنها صالحة كجزء من كود
        f_code = (farm_code or "UNK").upper().replace(" ", "")[:6]
        c_code = (crop_code or "GEN").upper().replace(" ", "")[:6]
        date_str = date.strftime('%Y%m%d')
        
        # إضافة جزء عشوائي قصير لمنع التكرار في نفس اليوم
        unique_suffix = uuid.uuid4().hex[:4].upper()
        
        return f"{f_code}-{c_code}-{date_str}-{unique_suffix}"

    @staticmethod
    def get_batch_metadata(activity):
        """
        تجهيز البيانات الوصفية للطباعة على الملصقات (QR Code Data)
        """
        return {
            "batch_number": activity.batch_number,
            "harvest_date": activity.start_time.isoformat() if hasattr(activity, 'start_time') and activity.start_time else None,
            "farm": activity.location.farm.name if activity.location and activity.location.farm else "Unknown",
            "crop": activity.crop.name if activity.crop else "Unknown",
            "supervisor": activity.log.supervisor.get_full_name() if activity.log and activity.log.supervisor else "System"
        }
