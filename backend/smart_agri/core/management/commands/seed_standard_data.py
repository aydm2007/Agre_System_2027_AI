from django.core.management.base import BaseCommand
from smart_agri.core.models import Crop, Task

CROPS_DATA = [
    {
        'name': 'قمح (Wheat)',
        'mode': 'Open',
        'is_perennial': False,
        'tasks': [
            {'stage': 'تجهيز الأرض', 'name': 'حراثة أولى', 'requires_machinery': True},
            {'stage': 'تجهيز الأرض', 'name': 'حراثة ثانية وتنعيم', 'requires_machinery': True},
            {'stage': 'البذر', 'name': 'بذر الحبوب', 'requires_area': True, 'requires_machinery': True},
            {'stage': 'الري', 'name': 'رية الإنبات', 'requires_well': True},
            {'stage': 'التسميد', 'name': 'تسميد يوريا (دفعة أولى)', 'requires_area': True},
            {'stage': 'الري', 'name': 'رية المحاية', 'requires_well': True},
            {'stage': 'مكافحة', 'name': 'رش مبيد حشائش', 'requires_area': True},
            {'stage': 'الحصاد', 'name': 'حصاد آلي', 'is_harvest_task': True, 'requires_machinery': True},
        ]
    },
    {
        'name': 'ذرة شامية (Corn)',
        'mode': 'Open',
        'is_perennial': False,
        'tasks': [
            {'stage': 'تجهيز الأرض', 'name': 'حراثة عميقة', 'requires_machinery': True},
            {'stage': 'تجهيز الأرض', 'name': 'تخطيط الأرض', 'requires_machinery': True},
            {'stage': 'الزراعة', 'name': 'زراعة البذور', 'requires_area': True},
            {'stage': 'الري', 'name': 'رية الزراعة', 'requires_well': True},
            {'stage': 'التسميد', 'name': 'تسميد سوبر', 'requires_area': True},
            {'stage': 'مكافحة', 'name': 'رش دودة الحشد', 'requires_area': True},
            {'stage': 'الحصاد', 'name': 'قطع وتجفيف', 'is_harvest_task': True},
        ]
    },
    {
        'name': 'طماطم (Tomato - Open)',
        'mode': 'Open',
        'is_perennial': False,
        'tasks': [
            {'stage': 'المشتل', 'name': 'تجهيز صواني الشتلات', 'requires_area': False},
            {'stage': 'تجهيز الأرض', 'name': 'فرد شبكة الري', 'requires_machinery': False, 'requires_well': True},
            {'stage': 'الزراعة', 'name': 'نقل الشتلات للأرض', 'requires_area': True},
            {'stage': 'تسميد', 'name': 'تسميد NPK متوازن', 'requires_area': True},
            {'stage': 'مكافحة', 'name': 'رش وقائي فطري', 'requires_area': True},
            {'stage': 'الحصاد', 'name': 'جني المحصول (قطفة أولى)', 'is_harvest_task': True},
            {'stage': 'الحصاد', 'name': 'جني المحصول (قطفة ثانية)', 'is_harvest_task': True},
        ]
    },
    {
        'name': 'بطاطس (Potato)',
        'mode': 'Open',
        'is_perennial': False,
        'tasks': [
            {'stage': 'تجهيز الدرنات', 'name': 'تقطيع وتعقيم التقاوي', 'requires_area': False},
            {'stage': 'تجهيز الأرض', 'name': 'حرث وتسوية', 'requires_machinery': True},
            {'stage': 'الزراعة', 'name': 'زراعة التقاوي', 'requires_area': True, 'requires_machinery': True},
            {'stage': 'الري', 'name': 'ري محوري/تنقيط', 'requires_well': True},
            {'stage': 'تحضين', 'name': 'تكويم التراب (تحضين)', 'requires_machinery': True},
            {'stage': 'الحصاد', 'name': 'قلع البطاطس', 'is_harvest_task': True, 'requires_machinery': True},
        ]
    },
    {
        'name': 'بصل (Onion)',
        'mode': 'Open',
        'is_perennial': False,
        'tasks': [
            {'stage': 'المشتل', 'name': 'زراعة البذور في المشتل', 'requires_area': False},
            {'stage': 'تجهيز الأرض', 'name': 'تجهيز الخطوط', 'requires_machinery': True},
            {'stage': 'الزراعة', 'name': 'شتل البصل', 'requires_area': True},
            {'stage': 'ري وتسميد', 'name': 'ري وتسميد دوري', 'requires_well': True},
            {'stage': 'الحصاد', 'name': 'تقليع وتجفيف', 'is_harvest_task': True},
        ]
    }
]

class Command(BaseCommand):
    help = 'Seeding standard Yemeni crops and tasks'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting Standard Data Seeding...'))

        for crop_data in CROPS_DATA:
            tasks_data = crop_data.pop('tasks')
            
            # Create/Update Crop
            crop, created = Crop.objects.update_or_create(
                name=crop_data['name'],
                mode=crop_data['mode'],
                defaults={'is_perennial': crop_data['is_perennial']}
            )
            
            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{action} Crop: {crop}'))

            # Create/Update Tasks
            for t_data in tasks_data:
                Task.objects.update_or_create(
                    crop=crop,
                    name=t_data['name'],
                    defaults={
                        'stage': t_data['stage'],
                        'requires_area': t_data.get('requires_area', False),
                        'requires_machinery': t_data.get('requires_machinery', False),
                        'requires_well': t_data.get('requires_well', False),
                        'is_harvest_task': t_data.get('is_harvest_task', False),
                    }
                )
        
        self.stdout.write(self.style.SUCCESS('Seeding Completed Successfully!'))
