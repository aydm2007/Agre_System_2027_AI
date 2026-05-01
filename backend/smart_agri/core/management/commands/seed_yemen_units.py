from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from smart_agri.core.models import Unit, UnitConversion


UNIT_DEFINITIONS = [
    # الكتل القياسية
    {
        'code': 'kg',
        'name': 'كيلوغرام',
        'symbol': 'كجم',
        'category': Unit.CATEGORY_MASS,
        'precision': 3,
    },
    {
        'code': 'ton',
        'name': 'طن متري',
        'symbol': 'طن',
        'category': Unit.CATEGORY_MASS,
        'precision': 3,
    },
    {
        'code': 'g',
        'name': 'جرام',
        'symbol': 'جم',
        'category': Unit.CATEGORY_MASS,
        'precision': 3,
    },
    {
        'code': 'bag',
        'name': 'كيس (شوال)',
        'symbol': 'كيس',
        'category': Unit.CATEGORY_MASS,
        'precision': 3,
        'metadata': {'notes': 'شوال حبوب قياسي 50 كجم'},
    },
    {
        'code': 'bundle',
        'name': 'حزمة',
        'symbol': 'حزمة',
        'category': Unit.CATEGORY_COUNT,
        'precision': 0,
    },
    {
        'code': 'piece',
        'name': 'قطعة',
        'symbol': 'قطعة',
        'category': Unit.CATEGORY_COUNT,
        'precision': 0,
    },
    {
        'code': 'tree',
        'name': 'شجرة',
        'symbol': 'شجرة',
        'category': Unit.CATEGORY_COUNT,
        'precision': 0,
    },
    # وحدات الحجم
    {
        'code': 'm3',
        'name': 'متر مكعب',
        'symbol': 'م³',
        'category': Unit.CATEGORY_VOLUME,
        'precision': 3,
    },
    {
        'code': 'L',
        'name': 'لتر',
        'symbol': 'لتر',
        'category': Unit.CATEGORY_VOLUME,
        'precision': 3,
    },
    {
        'code': 'ml',
        'name': 'مليلتر',
        'symbol': 'مل',
        'category': Unit.CATEGORY_VOLUME,
        'precision': 3,
    },
    # وحدات المساحة المعتمدة محلياً
    {
        'code': 'm2',
        'name': 'متر مربع',
        'symbol': 'م²',
        'category': Unit.CATEGORY_AREA,
        'precision': 3,
    },
    {
        'code': 'hectare',
        'name': 'هكتار',
        'symbol': 'هكتار',
        'category': Unit.CATEGORY_AREA,
        'precision': 3,
    },
    {
        'code': 'libnah',
        'name': 'لبنة (صنعاني)',
        'symbol': 'لبنة',
        'category': Unit.CATEGORY_AREA,
        'precision': 2,
        'metadata': {'notes': 'وحدة مساحة (صنعاء). تعادل تقليدياً 44.44 متر مربع (تختلف حسب المنطقة).'}
    },
    {
        'code': 'dunum',
        'name': 'دونم',
        'symbol': 'دونم',
        'category': Unit.CATEGORY_AREA,
        'precision': 3,
        'metadata': {'notes': 'وحدة مساحة شائعة في اليمن والشرق الأوسط. تعادل 1000 متر مربع.'}
    },
    {
        'code': 'qasab',
        'name': 'قصبة (عياري)', # Renamed to generic/standard
        'symbol': 'قصبة',
        'category': Unit.CATEGORY_AREA,
        'precision': 3,
        'metadata': {'notes': 'الافتراضي: 45 م². يرجى تعديل معامل التحويل حسب العرف المحلي للمزرعة.'},
    },
    {
        'code': 'maad',
        'name': 'معاد (تهامي قياسي)', # Renamed for legal clarity
        'symbol': 'معاد',
        'category': Unit.CATEGORY_AREA,
        'precision': 3,
        'metadata': {'notes': 'يعادل 720 متر مربع (16 قصبة). يرجى التحقق من العرف المحلي.'}
    },
    {
        'code': 'gaduh',
        'name': 'قدح (مكيال)', # Essential for Zakat/Cereals
        'symbol': 'قدح',
        'category': Unit.CATEGORY_VOLUME, # It's volume, not mass
        'precision': 2,
        'metadata': {'notes': 'مكيال تقليدي للحبوب. الوزن يختلف بحسب الكثافة (قمح/ذرة).'}
    },
    # وحدات العبوات
    {
        'code': 'carton',
        'name': 'كرتون',
        'symbol': 'كرتون',
        'category': Unit.CATEGORY_COUNT,
        'precision': 0,
        'metadata': {'notes': 'عبوة تعبئة (افتراضي 12 حبة)'}
    },
]


# معاملات التحويل (يمكن تعديلها لتناسب كل منطقة)
UNIT_CONVERSIONS = [
    ('ton', 'kg', Decimal('1000')),
    ('kg', 'g', Decimal('1000')),
    ('bag', 'kg', Decimal('50')),      # شوال: 50 كجم
    ('bundle', 'piece', Decimal('1')),
    ('carton', 'piece', Decimal('12')),
    ('m3', 'L', Decimal('1000')),
    ('L', 'ml', Decimal('1000')),
    ('libnah', 'm2', Decimal('44.44')), # Standard approximation
    ('dunum', 'm2', Decimal('1000')),   # دونم = 1000 متر مربع
    ('hectare', 'm2', Decimal('10000')), # هكتار = 10000 متر مربع
    ('qasab', 'm2', Decimal('45')),    # قصبة ≈ 45 متر مربع (قيمة تقريبية شائعة)
    ('maad', 'm2', Decimal('720')),    # معاد ≈ 16 قصبة -> 16 * 45 = 720 م²
    ('maad', 'qasab', Decimal('16')),
]


UNITS_TO_REMOVE = ['feddan', 'kirat']


class Command(BaseCommand):
    help = 'تنظيف الوحدات الحالية وإضافة وحدات القياس المتداولة في اليمن مع التحويلات'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('بدء عملية تحديث الوحدات...'))
        now = timezone.now()

        # إزالة الوحدات غير المستخدمة
        removed_units = list(Unit.objects.filter(code__in=UNITS_TO_REMOVE))
        if removed_units:
            Unit.objects.filter(code__in=UNITS_TO_REMOVE).delete()
            for unit in removed_units:
                self.stdout.write(
                    self.style.WARNING(f'- تم حذف الوحدة {unit.code} ({unit.name})')
                )
        else:
            self.stdout.write('لا توجد وحدات محذوفة.')

        # إنشاء / تحديث الوحدات
        code_to_unit = {}
        for data in UNIT_DEFINITIONS:
            defaults = {
                'name': data['name'],
                'symbol': data.get('symbol', data['code']),
                'category': data['category'],
                'precision': data.get('precision', 3),
                'metadata': data.get('metadata', {}),
            }
            unit, created = Unit.objects.update_or_create(
                code=data['code'],
                defaults=defaults,
            )
            action = 'إضافة' if created else 'تحديث'
            self.stdout.write(self.style.SUCCESS(f'{action} الوحدة: {unit.code} ({unit.name})'))
            code_to_unit[unit.code] = unit

        # إضافة التحويلات
        for from_code, to_code, multiplier in UNIT_CONVERSIONS:
            from_unit = code_to_unit.get(from_code)
            to_unit = code_to_unit.get(to_code)

            if not from_unit or not to_unit:
                self.stdout.write(
                    self.style.ERROR(
                        f'تخطي التحويل {from_code} -> {to_code}: إحدى الوحدات غير موجودة'
                    )
                )
                continue

            conversion, created = UnitConversion.objects.update_or_create(
                from_unit=from_unit,
                to_unit=to_unit,
                defaults={'multiplier': multiplier, 'updated_at': now},
            )
            action = 'إضافة تحويل' if created else 'تحديث تحويل'
            self.stdout.write(self.style.SUCCESS(
                f'{action}: {from_code} -> {to_code} = {multiplier}'
            ))

        self.stdout.write(self.style.SUCCESS('اكتملت عملية تحديث الوحدات والتحويلات.'))
