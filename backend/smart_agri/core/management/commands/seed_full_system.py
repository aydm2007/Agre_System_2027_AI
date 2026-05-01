"""
[AGRI-GUARDIAN] Full System Seeder - بذر النظام الشامل
=====================================================
Seeds: Golden Farm + Sardud + Al-Jaruba + Users + Roles + Complete Document Cycles.
Includes: perennial crops (Mango, Banana), seasonal crops (Wheat),
         financial cycle, harvest, sales, and inventory.

Usage:
    python manage.py seed_full_system --verbose
    python manage.py seed_full_system --clean --verbose
"""

import logging
import os
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from django.utils.crypto import get_random_string

logger = logging.getLogger(__name__)

User = get_user_model()


# ═══════════════════════════════════════════════════════════
# User Definitions (Arabic names, roles, farm assignments)
# ═══════════════════════════════════════════════════════════
USER_DEFINITIONS = [
    {
        'username': 'farm_manager',
        'first_name': 'عبدالله',
        'last_name': 'المدير',
        'email': 'manager@yeco.ye',
        'group': 'مدير المزرعة',
        'farms': ['sardud', 'jaruba'],
        'membership_role': 'مدير المزرعة',
        'is_staff': True,
    },
    {
        'username': 'accountant',
        'first_name': 'أحمد',
        'last_name': 'المحاسب',
        'email': 'accountant@yeco.ye',
        'group': 'محاسب المزرعة',
        'farms': ['sardud', 'jaruba'],
        'membership_role': 'محاسب المزرعة',
    },
    {
        'username': 'technician',
        'first_name': 'خالد',
        'last_name': 'الفني',
        'email': 'tech@yeco.ye',
        'group': 'فني زراعي',
        'farms': ['sardud', 'jaruba'],
        'membership_role': 'فني زراعي',
    },
    {
        'username': 'supervisor',
        'first_name': 'ياسر',
        'last_name': 'المشرف',
        'email': 'supervisor@yeco.ye',
        'group': 'مشرف ميداني',
        'farms': ['sardud', 'jaruba'],
        'membership_role': 'مشرف ميداني',
    },
    {
        'username': 'cashier',
        'first_name': 'سلطان',
        'last_name': 'الخزنة',
        'email': 'cashier@yeco.ye',
        'group': 'أمين صندوق',
        'farms': ['sardud'],
        'membership_role': 'أمين صندوق',
    },
    {
        'username': 'storekeeper',
        'first_name': 'فيصل',
        'last_name': 'المستودع',
        'email': 'store@yeco.ye',
        'group': 'أمين مخزن',
        'farms': ['sardud', 'jaruba'],
        'membership_role': 'أمين مخزن',
    },
    {
        'username': 'farmer_user',
        'first_name': 'محسن',
        'last_name': 'المزارع',
        'email': 'farmer@yeco.ye',
        'group': 'مزارع',
        'farms': ['sardud'],
        'membership_role': 'مزارع',
    },
    {
        'username': 'chief_acct',
        'first_name': 'ناصر',
        'last_name': 'كبير المحاسبين',
        'email': 'chief@yeco.ye',
        'group': 'رئيس حسابات القطاع',
        'farms': ['sardud', 'jaruba', 'golden'],
        'membership_role': 'رئيس حسابات القطاع',
        'is_staff': True,
    },
    {
        'username': 'finance_dir',
        'first_name': 'عمر',
        'last_name': 'المالية',
        'email': 'finance@yeco.ye',
        'group': 'المدير المالي لقطاع المزارع',
        'farms': ['sardud', 'jaruba', 'golden'],
        'membership_role': 'المدير المالي لقطاع المزارع',
        'is_staff': True,
    },
    {
        'username': 'golden_manager',
        'first_name': 'مدير',
        'last_name': 'الذهبية',
        'email': 'golden@yeco.ye',
        'group': 'مدير المزرعة',
        'farms': ['golden'],
        'membership_role': 'مدير المزرعة',
        'is_staff': True,
    },
]


class Command(BaseCommand):
    help = '[AGRI-GUARDIAN] بذر النظام الشامل: Golden Farm + سردود + الجروبة + المستخدمين والأدوار'

    def add_arguments(self, parser):
        parser.add_argument('--clean', action='store_true', help='تنظيف المزارع غير المطلوبة أولاً')
        parser.add_argument('--verbose', action='store_true', help='عرض التفاصيل')
        parser.add_argument('--default-password', dest='default_password', help='كلمة المرور الافتراضية للمستخدمين التجريبيين')

    @transaction.atomic
    def handle(self, *args, **options):
        self.verbose = options.get('verbose', False)
        self.default_password = self._resolve_default_password(options)
        self._header('🌾 AGRI-GUARDIAN: بذر النظام الشامل')

        # Phase 0: Clean stale farms if requested
        if options.get('clean'):
            self._clean_stale_farms()

        # Phase 1: Seed Roles/Groups
        self._phase('📋 المرحلة 1: إنشاء الأدوار والصلاحيات')
        try:
            call_command('seed_roles', verbosity=0)
            self._ok('تم إنشاء/تحديث الأدوار')
        except Exception as e:
            logger.exception("seed_roles failed")
            self._warn(f'seed_roles skipped: {e}')

        # Phase 2: Seed Golden Farm
        self._phase('🏆 المرحلة 2: المزرعة الذهبية (Golden Farm)')
        golden_farm = None

        # Phase 3: Seed Sardud Farm with full document cycle
        self._phase('🌴 المرحلة 3: مزرعة سردود - دورة مستندية كاملة')
        sardud_farm = self._seed_sardud_farm()

        # Jaruba seeding disabled in Sardud-only canonical mode
        jaruba_farm = None


        # Phase 5: Create Users with Roles
        self._phase('👥 المرحلة 5: إنشاء المستخدمين والصلاحيات')
        farm_map = {
            'sardud': sardud_farm,


        }
        self._create_users(farm_map)

        self._print_final_summary(None, sardud_farm, None)


    # ═══════════════════════════════════════════════════════════
    # GOLDEN FARM
    # ═══════════════════════════════════════════════════════════
    def _seed_golden_farm(self):
        """Seed Golden Farm using existing command or create minimal data."""
        from smart_agri.core.models import Farm
        try:
            call_command('seed_golden_farm', verbosity=0)
            farm = Farm.objects.filter(slug='golden-farm').first()
            if farm:
                self._ok(f'المزرعة الذهبية: {farm.name}')
                return farm
        except Exception as e:
            logger.exception("seed_golden_farm failed")
            self._warn(f'seed_golden_farm failed: {e}')

        # Fallback: create minimal golden farm
        farm, created = Farm.objects.get_or_create(
            slug='golden-farm',
            defaults={
                'name': 'المزرعة الذهبية - Golden Farm',
                'region': 'منطقة صنعاء الزراعية',
                'area': Decimal('150.00'),
                'description': 'مزرعة نموذجية متكاملة لاختبار النظام',
            }
        )
        self._ok(f'المزرعة الذهبية: {farm.name} ({"جديدة" if created else "موجودة"})')
        return farm

    # ═══════════════════════════════════════════════════════════
    # SARDUD FARM - Complete Document Cycle
    # ═══════════════════════════════════════════════════════════
    def _seed_sardud_farm(self):
        from smart_agri.core.models import Farm, Location, Asset, Employee, Crop, CropVariety, Task
        from smart_agri.core.models import Season, CropPlan, CropPlanBudgetLine
        from smart_agri.core.models import Activity, DailyLog, ActivityEmployee
        from smart_agri.core.models import HarvestLot, LaborRate, MachineRate
        from smart_agri.inventory.models import Unit, Item, ItemInventory, ItemInventoryBatch
        from smart_agri.finance.models import (
            FiscalYear, FiscalPeriod, FinancialLedger,
            BudgetClassification, CostConfiguration, SectorRelationship,
        )
        from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer
        from smart_agri.accounts.models import FarmGovernanceProfile

        admin_user = User.objects.filter(username='ibrahim').first() or User.objects.first()

        # ── Farm ──
        farm, created = Farm.objects.get_or_create(
            name='مزرعة سردود',
            defaults={
                'slug': 'sardud',
                'region': 'وادي سردود - الحديدة',
                'area': Decimal('1500.00'),
                'description': 'مزرعة رئيسية في وادي سردود - محاصيل معمرة وموسمية',
            }
        )
        self._ok(f'مزرعة سردود: {farm.name}')

        # ── Governance Profile ──
        FarmGovernanceProfile.objects.get_or_create(
            farm=farm,
            defaults={'tier': 'LARGE', 'rationale': 'مساحة أكبر من 250 هكتار'}
        )

        # ── Locations ──
        locations_data = [
            {'name': 'قطعة 1 - بستان المانجو', 'code': 'SARD-MNG', 'type': 'Orchard'},
            {'name': 'قطعة 2 - حقل الموز', 'code': 'SARD-BAN', 'type': 'Field'},
            {'name': 'قطعة 3 - حقل القمح', 'code': 'SARD-WHT', 'type': 'Field'},
            {'name': 'مستودع المواد', 'code': 'SARD-STORE', 'type': 'Service'},
            {'name': 'منطقة الآبار', 'code': 'SARD-WELL', 'type': 'Service'},
        ]
        locations = {}
        for loc_data in locations_data:
            loc, _ = Location.objects.get_or_create(
                farm=farm, code=loc_data['code'],
                defaults=loc_data
            )
            locations[loc_data['code']] = loc
        self._log(f'  المواقع: {len(locations)}')

        # ── Units ──
        unit_kg, _ = Unit.objects.get_or_create(code='KG', defaults={'name': 'كيلوغرام', 'symbol': 'kg'})
        unit_ton, _ = Unit.objects.get_or_create(code='TON', defaults={'name': 'طن', 'symbol': 'ton'})
        unit_liter, _ = Unit.objects.get_or_create(code='L', defaults={'name': 'لتر', 'symbol': 'L'})

        # ── Crops (Perennial + Seasonal) ──
        mango, _ = Crop.objects.get_or_create(
            name='مانجو', defaults={'mode': 'Open', 'is_perennial': True, 'max_yield_per_ha': Decimal('15.0')}
        )
        banana, _ = Crop.objects.get_or_create(
            name='موز', defaults={'mode': 'Open', 'is_perennial': True, 'max_yield_per_ha': Decimal('30.0')}
        )
        wheat, _ = Crop.objects.get_or_create(
            name='قمح', defaults={'mode': 'Open', 'is_perennial': False, 'max_yield_per_ha': Decimal('5.0')}
        )
        self._log('  المحاصيل: مانجو، موز، قمح')

        # ── Varieties ──
        mango_var, _ = CropVariety.objects.get_or_create(
            crop=mango, name='تيمور', defaults={'est_days_to_harvest': 120}
        )
        banana_var, _ = CropVariety.objects.get_or_create(
            crop=banana, name='بلدي', defaults={'est_days_to_harvest': 270}
        )
        wheat_var, _ = CropVariety.objects.get_or_create(
            crop=wheat, name='محلي محسن', defaults={'est_days_to_harvest': 120}
        )

        # ── Tasks ──
        tasks = {}
        tasks_data = [
            {'name': 'ري بالغمر', 'crop': mango, 'stage': 'الرعاية', 'requires_well': True},
            {'name': 'ري بالتنقيط', 'crop': banana, 'stage': 'الرعاية', 'requires_well': True},
            {'name': 'تسميد', 'crop': mango, 'stage': 'الرعاية'},
            {'name': 'رش مبيدات', 'crop': mango, 'stage': 'الحماية', 'requires_machinery': True},
            {'name': 'حراثة', 'crop': wheat, 'stage': 'التحضير', 'requires_machinery': True},
            {'name': 'زراعة القمح', 'crop': wheat, 'stage': 'الزراعة'},
            {'name': 'حصاد المانجو', 'crop': mango, 'stage': 'الحصاد', 'is_harvest_task': True},
            {'name': 'حصاد الموز', 'crop': banana, 'stage': 'الحصاد', 'is_harvest_task': True},
            {'name': 'حصاد القمح', 'crop': wheat, 'stage': 'الحصاد', 'is_harvest_task': True},
        ]
        for t in tasks_data:
            crop = t.pop('crop')
            task_name = t.pop('name')
            task = Task.objects.filter(name=task_name, crop=crop).first()
            if not task:
                task = Task.objects.create(
                    name=task_name, crop=crop,
                    stage=t.get('stage', ''),
                    requires_well=t.get('requires_well', False),
                    requires_machinery=t.get('requires_machinery', False),
                    is_harvest_task=t.get('is_harvest_task', False),
                )
            tasks[task_name] = task
        self._log(f'  المهام الزراعية: {len(tasks)}')

        # ── Assets ──
        assets_data = [
            {'name': 'بئر ارتوازي سردود 1', 'code': 'WELL-S01', 'category': 'Well'},
            {'name': 'بئر ارتوازي سردود 2', 'code': 'WELL-S02', 'category': 'Well'},
            {'name': 'جرار ماسي فيرجسون 375', 'code': 'TRACT-S01', 'category': 'Machinery'},
            {'name': 'رشاش مبيدات محمول', 'code': 'SPRAY-S01', 'category': 'Machinery'},
            {'name': 'شاحنة نقل هيلوكس', 'code': 'TRUCK-S01', 'category': 'Vehicle'},
            {'name': 'نظام ري بالتنقيط', 'code': 'IRR-S01', 'category': 'Irrigation'},
        ]
        assets = {}
        for a in assets_data:
            asset, _ = Asset.objects.get_or_create(
                farm=farm, code=a['code'],
                defaults={'name': a['name'], 'category': a['category'], 'purchase_value': Decimal('50000.00')}
            )
            assets[a['code']] = asset
        self._log(f'  الأصول: {len(assets)}')

        # ── Employees ──
        employees_data = [
            {'first_name': 'أحمد', 'last_name': 'الحارثي', 'employee_id': 'SARD-001', 'role': 'Manager', 'category': 'OFFICIAL', 'payment_mode': 'OFFICIAL', 'base_salary': Decimal('80000.0000')},
            {'first_name': 'علي', 'last_name': 'العمري', 'employee_id': 'SARD-002', 'role': 'Engineer', 'category': 'OFFICIAL', 'payment_mode': 'OFFICIAL', 'base_salary': Decimal('60000.0000')},
            {'first_name': 'محمد', 'last_name': 'الصنعاني', 'employee_id': 'SARD-003', 'role': 'Worker', 'category': 'CASUAL', 'payment_mode': 'SURRA', 'shift_rate': Decimal('3000.0000')},
            {'first_name': 'عبدالرحمن', 'last_name': 'الأحمدي', 'employee_id': 'SARD-004', 'role': 'Worker', 'category': 'CASUAL', 'payment_mode': 'SURRA', 'shift_rate': Decimal('2500.0000')},
            {'first_name': 'يوسف', 'last_name': 'القاضي', 'employee_id': 'SARD-005', 'role': 'Worker', 'category': 'CASUAL', 'payment_mode': 'SURRA', 'shift_rate': Decimal('2500.0000')},
            {'first_name': 'سعيد', 'last_name': 'المرادي', 'employee_id': 'SARD-006', 'role': 'Worker', 'category': 'CASUAL', 'payment_mode': 'SURRA', 'shift_rate': Decimal('3000.0000')},
        ]
        employees = []
        for emp_data in employees_data:
            emp, _ = Employee.objects.get_or_create(
                farm=farm, employee_id=emp_data['employee_id'],
                defaults={
                    'first_name': emp_data['first_name'],
                    'last_name': emp_data['last_name'],
                    'role': emp_data['role'],
                    'category': emp_data['category'],
                    'payment_mode': emp_data['payment_mode'],
                    'base_salary': emp_data.get('base_salary', Decimal('0.0000')),
                    'shift_rate': emp_data.get('shift_rate', Decimal('0.0000')),
                    'joined_date': date(2025, 1, 1),
                    'is_active': True,
                }
            )
            employees.append(emp)
        self._log(f'  الموظفون: {len(employees)}')

        # ── Labor & Machine Rates ──
        LaborRate.objects.update_or_create(
            farm=farm, role_name='عامل يومي', effective_date=date(2026, 1, 1),
            defaults={'daily_rate': Decimal('3000.00'), 'cost_per_hour': Decimal('375.00'), 'currency': 'YER'}
        )
        for asset in Asset.objects.filter(farm=farm, category='Machinery'):
            MachineRate.objects.update_or_create(
                asset=asset,
                defaults={'daily_rate': Decimal('5000.00'), 'cost_per_hour': Decimal('625.00'), 'fuel_consumption_rate': Decimal('10.0')}
            )

        # ── Inventory ──
        items_data = [
            {'name': 'بذور قمح محسنة', 'group': 'Seeds', 'unit_price': Decimal('800.00'), 'uom': 'kg'},
            {'name': 'سماد يوريا 46%', 'group': 'Fertilizers', 'unit_price': Decimal('400.00'), 'uom': 'kg'},
            {'name': 'سماد NPK 15-15-15', 'group': 'Fertilizers', 'unit_price': Decimal('600.00'), 'uom': 'kg'},
            {'name': 'مبيد فطري ريدوميل', 'group': 'Pesticides', 'unit_price': Decimal('2500.00'), 'uom': 'L'},
            {'name': 'مبيد حشري ملاثيون', 'group': 'Pesticides', 'unit_price': Decimal('1800.00'), 'uom': 'L'},
            {'name': 'ديزل', 'group': 'Fuel', 'unit_price': Decimal('250.00'), 'uom': 'L'},
        ]
        items = []
        storage_loc = locations.get('SARD-STORE')
        for item_data in items_data:
            item, _ = Item.objects.get_or_create(
                name=item_data['name'], group=item_data['group'],
                defaults={'unit_price': item_data['unit_price'], 'uom': item_data['uom']}
            )
            items.append(item)
            # Initialize inventory
            if storage_loc:
                inv, _ = ItemInventory.objects.get_or_create(
                    farm=farm, item=item, location=storage_loc,
                    defaults={'qty': Decimal('500.00')}
                )
                ItemInventoryBatch.objects.get_or_create(
                    inventory=inv, batch_number=f'SARD-{item.name[:8]}-2026',
                    defaults={'qty': Decimal('500.00'), 'expiry_date': date(2027, 1, 1)}
                )
        self._log(f'  المواد والمخزون: {len(items)}')

        # ── Season ──
        season, _ = Season.objects.get_or_create(
            name='موسم 2026 الزراعي',
            defaults={'start_date': date(2026, 1, 1), 'end_date': date(2026, 12, 31), 'is_active': True}
        )

        # ── Crop Plans ──
        plan_data = [
            {'crop': mango, 'loc': 'SARD-MNG', 'area': Decimal('80'), 'yield': Decimal('1200'), 'name': 'خطة إنتاج المانجو 2026'},
            {'crop': banana, 'loc': 'SARD-BAN', 'area': Decimal('50'), 'yield': Decimal('1500'), 'name': 'خطة إنتاج الموز 2026'},
            {'crop': wheat, 'loc': 'SARD-WHT', 'area': Decimal('40'), 'yield': Decimal('200'), 'name': 'خطة إنتاج القمح 2026'},
        ]
        crop_plans = []
        for pd in plan_data:
            plan, _ = CropPlan.objects.get_or_create(
                farm=farm, season=season, location=locations[pd['loc']], crop=pd['crop'],
                defaults={
                    'name': pd['name'],
                    'area': pd['area'],
                    'expected_yield': pd['yield'],
                    'status': 'active',
                    'start_date': season.start_date,
                    'end_date': season.end_date,
                }
            )
            crop_plans.append(plan)
            # Budget lines
            for cat, amt in [('materials', Decimal('500000')), ('labor', Decimal('800000')), ('machinery', Decimal('300000'))]:
                CropPlanBudgetLine.objects.get_or_create(
                    crop_plan=plan, category=cat,
                    defaults={'total_budget': amt}
                )
        self._log(f'  خطط المحاصيل: {len(crop_plans)}')

        # ── Budget Classifications ──
        budget_codes = [
            ('2111', 'وقود وزيوت'),
            ('2121', 'أسمدة ومخصبات'),
            ('2122', 'مبيدات'),
            ('2131', 'بذور وشتلات'),
            ('3112', 'صيانة آليات'),
            ('4111', 'أجور عمالة يومية'),
        ]
        for code, name in budget_codes:
            BudgetClassification.objects.get_or_create(code=code, defaults={'name_ar': name})
        self._log('  بنود الموازنة')

        # ── Fiscal Year & Periods ──
        fiscal_year, _ = FiscalYear.objects.get_or_create(
            farm=farm, year=2026,
            defaults={'start_date': date(2026, 1, 1), 'end_date': date(2026, 12, 31), 'is_closed': False}
        )
        for month in range(1, 13):
            start = date(2026, month, 1)
            end = date(2026, 12, 31) if month == 12 else date(2026, month + 1, 1) - timedelta(days=1)
            FiscalPeriod.objects.get_or_create(
                fiscal_year=fiscal_year, month=month,
                defaults={'start_date': start, 'end_date': end, 'is_closed': False}
            )
        self._log('  السنة المالية: 2026 (12 فترة)')

        # ── Cost Configuration ──
        CostConfiguration.objects.get_or_create(
            farm=farm,
            defaults={
                'currency': 'YER',
                'effective_date': date(2026, 1, 1),
            }
        )

        # ── Sector Relationship ──
        SectorRelationship.objects.get_or_create(
            farm=farm,
            defaults={
                'current_balance': Decimal('0.0000'),
                'allow_revenue_recycling': False,
            }
        )

        # ── DOCUMENT CYCLE: Daily Logs + Activities ──
        self._phase('  📝 الدورة المستندية - سردود')
        daily_logs = []
        for days_ago in range(14, 0, -1):
            log_date = date.today() - timedelta(days=days_ago)
            if log_date.weekday() >= 5:  # Skip weekends
                continue
            log = DailyLog.objects.filter(farm=farm, log_date=log_date).first()
            if not log:
                log = DailyLog.objects.create(
                    farm=farm, log_date=log_date,
                    status='approved',
                    notes=f'سجل يومي مزرعة سردود - {log_date}',
                    created_by=admin_user,
                    approved_by=admin_user,
                    approved_at=timezone.now(),
                )
            daily_logs.append(log)

        # Create activities for each day
        task_rotation = [
            ('ري بالغمر', mango, locations.get('SARD-MNG'), crop_plans[0]),
            ('تسميد', mango, locations.get('SARD-MNG'), crop_plans[0]),
            ('ري بالتنقيط', banana, locations.get('SARD-BAN'), crop_plans[1]),
            ('حراثة', wheat, locations.get('SARD-WHT'), crop_plans[2]),
            ('رش مبيدات', mango, locations.get('SARD-MNG'), crop_plans[0]),
        ]

        activities = []
        for i, log in enumerate(daily_logs[:10]):
            task_info = task_rotation[i % len(task_rotation)]
            task_name, crop, location, plan = task_info
            task_obj = tasks.get(task_name)
            if not task_obj:
                continue

            activity, created = Activity.objects.get_or_create(
                log=log, task=task_obj,
                defaults={
                    'crop': crop,
                    'location': location,
                    'crop_plan': plan,
                    'days_spent': Decimal('1.0'),
                    'cost_total': Decimal('5000.0000'),
                    'cost_labor': Decimal('3000.0000'),
                    'cost_materials': Decimal('2000.0000'),
                    'created_by': admin_user,
                    'data': {'note': f'نشاط {task_name} - مزرعة سردود'},
                }
            )
            if created:
                # Assign 2 workers
                for emp in employees[2:4]:
                    ActivityEmployee.objects.get_or_create(
                        activity=activity, employee=emp,
                        defaults={'surrah_share': Decimal('1.00')}
                    )
            activities.append(activity)
        self._ok(f'  السجلات اليومية: {len(daily_logs)}, الأنشطة: {len(activities)}')

        # ── Harvest ──
        harvest_lots = []
        for plan, crop, qty, harvest_date_offset in [
            (crop_plans[0], mango, Decimal('800'), 5),
            (crop_plans[2], wheat, Decimal('180'), 3),
        ]:
            lot, _ = HarvestLot.objects.get_or_create(
                farm=farm, crop=crop, crop_plan=plan,
                harvest_date=date.today() - timedelta(days=harvest_date_offset),
                defaults={
                    'quantity': qty,
                    'grade': 'First',
                    'location': plan.location,
                    'uom': 'kg',
                }
            )
            harvest_lots.append(lot)
        self._ok(f'  دفعات الحصاد: {len(harvest_lots)}')

        # ── Customers ──
        customer_wholesale, _ = Customer.objects.get_or_create(
            name='شركة الأمانة التجارية',
            defaults={'customer_type': 'wholesaler', 'phone': '+967-1-234567', 'address': 'صنعاء - شارع الستين'}
        )
        customer_retail, _ = Customer.objects.get_or_create(
            name='مؤسسة الحمدي للتجارة',
            defaults={'customer_type': 'retailer', 'phone': '+967-1-345678', 'address': 'الحديدة - شارع الكورنيش'}
        )

        # ── Sales Invoices ──
        for lot, customer, unit_price in [
            (harvest_lots[0], customer_wholesale, Decimal('150.00')),  # Mango
            (harvest_lots[1], customer_retail, Decimal('80.00')),  # Wheat
        ]:
            invoice, created = SalesInvoice.objects.get_or_create(
                farm=farm, customer=customer, invoice_date=date.today(),
                defaults={
                    'status': 'approved',
                    'total_amount': lot.quantity * unit_price,
                    'created_by': admin_user,
                }
            )
            if created and items:
                SalesInvoiceItem.objects.create(
                    invoice=invoice,
                    item=items[0],
                    description=f'حصاد {lot.crop.name} - مزرعة سردود',
                    qty=lot.quantity,
                    unit_price=unit_price,
                    total=lot.quantity * unit_price,
                    harvest_lot=lot,
                )
        self._ok('  فواتير المبيعات: 2')

        # ── Financial Ledger Entries ──
        # [AGRI-GUARDIAN] Seed realistic ledger entries for E2E cycle verification.
        ledger_count = 0

        # 1. Activity labor costs: Dr 1000-LABOR / Cr 2000-PAY-SAL
        for act in activities[:5]:
            try:
                FinancialLedger.objects.create(
                    farm=farm,
                    activity=act,
                    account_code=FinancialLedger.ACCOUNT_LABOR,
                    debit=act.cost_labor or Decimal('3000.0000'),
                    credit=Decimal('0'),
                    description=f'تكلفة عمالة - {act.task.name if act.task else "نشاط"}',
                    created_by=admin_user,
                )
                FinancialLedger.objects.create(
                    farm=farm,
                    activity=act,
                    account_code=FinancialLedger.ACCOUNT_PAYABLE_SALARIES,
                    debit=Decimal('0'),
                    credit=act.cost_labor or Decimal('3000.0000'),
                    description=f'مستحقات رواتب - {act.task.name if act.task else "نشاط"}',
                    created_by=admin_user,
                )
                ledger_count += 2
            except Exception as exc:
                logger.warning("Seed ledger entry skipped for activity %s: %s", act.pk, exc)

        # 2. Harvest lots: Dr 1300-INV-ASSET / Cr 4000-OVERHEAD
        for lot in harvest_lots:
            value = lot.quantity * Decimal('50.0000')  # Estimated cost per kg
            try:
                FinancialLedger.objects.create(
                    farm=farm,
                    account_code=FinancialLedger.ACCOUNT_INVENTORY_ASSET,
                    debit=value,
                    credit=Decimal('0'),
                    description=f'إضافة مخزون حصاد - {lot.crop.name}',
                    created_by=admin_user,
                )
                FinancialLedger.objects.create(
                    farm=farm,
                    account_code=FinancialLedger.ACCOUNT_OVERHEAD,
                    debit=Decimal('0'),
                    credit=value,
                    description=f'تكلفة إنتاج حصاد - {lot.crop.name}',
                    created_by=admin_user,
                )
                ledger_count += 2
            except Exception as exc:
                logger.warning("Seed ledger entry skipped for harvest lot %s: %s", lot.pk, exc)

        # 3. Sales invoices: Dr 1200-RECEIVABLE / Cr 5000-REVENUE
        for inv in SalesInvoice.objects.filter(farm=farm):
            try:
                FinancialLedger.objects.create(
                    farm=farm,
                    account_code=FinancialLedger.ACCOUNT_RECEIVABLE,
                    debit=inv.total_amount,
                    credit=Decimal('0'),
                    description=f'ذمم مدينة - فاتورة {inv.customer.name}',
                    created_by=admin_user,
                )
                FinancialLedger.objects.create(
                    farm=farm,
                    account_code=FinancialLedger.ACCOUNT_SALES_REVENUE,
                    debit=Decimal('0'),
                    credit=inv.total_amount,
                    description=f'إيراد مبيعات - فاتورة {inv.customer.name}',
                    created_by=admin_user,
                )
                ledger_count += 2
            except Exception as exc:
                logger.warning("Seed ledger entry skipped for invoice %s: %s", inv.pk, exc)

        self._ok(f'  القيود المالية: {ledger_count}')
        return farm

    # ═══════════════════════════════════════════════════════════
    # AL-JARUBA FARM
    # ═══════════════════════════════════════════════════════════
    def _seed_jaruba_farm(self):
        from smart_agri.core.models import Farm, Location, Asset, Employee, Crop, CropVariety, Task
        from smart_agri.core.models import Season, CropPlan, CropPlanBudgetLine
        from smart_agri.core.models import Activity, DailyLog, ActivityEmployee
        from smart_agri.core.models import HarvestLot, LaborRate
        from smart_agri.inventory.models import Unit, Item, ItemInventory
        from smart_agri.finance.models import FiscalYear, FiscalPeriod, CostConfiguration, SectorRelationship
        from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer
        from smart_agri.accounts.models import FarmGovernanceProfile

        admin_user = User.objects.filter(username='ibrahim').first() or User.objects.first()

        # ── Farm ──
        farm, created = Farm.objects.get_or_create(
            name='مزرعة الجروبة',
            defaults={
                'slug': 'jaruba',
                'region': 'وادي الجروبة - حجة',
                'area': Decimal('120.00'),
                'description': 'مزرعة متوسطة - إنتاج المانجو والموز',
            }
        )
        self._ok(f'مزرعة الجروبة: {farm.name}')

        # ── Governance ──
        FarmGovernanceProfile.objects.get_or_create(
            farm=farm,
            defaults={'tier': 'MEDIUM', 'rationale': 'مساحة بين 50 و 250 هكتار'}
        )

        # ── Locations ──
        locations_data = [
            {'name': 'قطعة 1 - مانجو مروي', 'code': 'JAR-MNG', 'type': 'Orchard'},
            {'name': 'قطعة 2 - موز بلدي', 'code': 'JAR-BAN', 'type': 'Field'},
            {'name': 'مستودع الجروبة', 'code': 'JAR-STORE', 'type': 'Service'},
        ]
        locations = {}
        for loc_data in locations_data:
            loc, _ = Location.objects.get_or_create(
                farm=farm, code=loc_data['code'], defaults=loc_data
            )
            locations[loc_data['code']] = loc

        # ── Use existing crops ──
        mango = Crop.objects.filter(name='مانجو').first()
        banana = Crop.objects.filter(name='موز').first()
        if not mango:
            mango, _ = Crop.objects.get_or_create(name='مانجو', defaults={'mode': 'Open', 'is_perennial': True})
        if not banana:
            banana, _ = Crop.objects.get_or_create(name='موز', defaults={'mode': 'Open', 'is_perennial': True})

        # ── Employees ──
        employees_data = [
            {'first_name': 'عبدالكريم', 'last_name': 'الجربي', 'employee_id': 'JAR-001', 'role': 'Manager', 'category': 'OFFICIAL', 'payment_mode': 'OFFICIAL', 'base_salary': Decimal('70000.0000')},
            {'first_name': 'حسن', 'last_name': 'الشرفي', 'employee_id': 'JAR-002', 'role': 'Worker', 'category': 'CASUAL', 'payment_mode': 'SURRA', 'shift_rate': Decimal('2500.0000')},
            {'first_name': 'ماجد', 'last_name': 'الحكيمي', 'employee_id': 'JAR-003', 'role': 'Worker', 'category': 'CASUAL', 'payment_mode': 'SURRA', 'shift_rate': Decimal('2500.0000')},
            {'first_name': 'طارق', 'last_name': 'المطري', 'employee_id': 'JAR-004', 'role': 'Worker', 'category': 'CASUAL', 'payment_mode': 'SURRA', 'shift_rate': Decimal('2000.0000')},
        ]
        employees = []
        for emp_data in employees_data:
            emp, _ = Employee.objects.get_or_create(
                farm=farm, employee_id=emp_data['employee_id'],
                defaults={
                    'first_name': emp_data['first_name'],
                    'last_name': emp_data['last_name'],
                    'role': emp_data['role'],
                    'category': emp_data['category'],
                    'payment_mode': emp_data['payment_mode'],
                    'base_salary': emp_data.get('base_salary', Decimal('0.0000')),
                    'shift_rate': emp_data.get('shift_rate', Decimal('0.0000')),
                    'joined_date': date(2025, 6, 1),
                    'is_active': True,
                }
            )
            employees.append(emp)
        self._log(f'  الموظفون: {len(employees)}')

        # ── Assets ──
        assets_data = [
            {'name': 'بئر الجروبة', 'code': 'WELL-J01', 'category': 'Well'},
            {'name': 'جرار زراعي صغير', 'code': 'TRACT-J01', 'category': 'Machinery'},
        ]
        for a in assets_data:
            Asset.objects.get_or_create(
                farm=farm, code=a['code'],
                defaults={'name': a['name'], 'category': a['category'], 'purchase_value': Decimal('30000.00')}
            )

        # ── Season & Plans ──
        season = Season.objects.filter(name='موسم 2026 الزراعي').first()
        if not season:
            season, _ = Season.objects.get_or_create(
                name='موسم 2026 الزراعي',
                defaults={'start_date': date(2026, 1, 1), 'end_date': date(2026, 12, 31), 'is_active': True}
            )

        crop_plans = []
        for crop, loc_code, name, area, yld in [
            (mango, 'JAR-MNG', 'خطة مانجو الجروبة 2026', Decimal('60'), Decimal('900')),
            (banana, 'JAR-BAN', 'خطة موز الجروبة 2026', Decimal('40'), Decimal('1200')),
        ]:
            plan, _ = CropPlan.objects.get_or_create(
                farm=farm, season=season, location=locations[loc_code], crop=crop,
                defaults={
                    'name': name, 'area': area, 'expected_yield': yld,
                    'status': 'active', 'start_date': season.start_date, 'end_date': season.end_date,
                }
            )
            crop_plans.append(plan)
            for cat, amt in [('materials', Decimal('300000')), ('labor', Decimal('500000'))]:
                CropPlanBudgetLine.objects.get_or_create(
                    crop_plan=plan, category=cat, defaults={'total_budget': amt}
                )

        # ── Fiscal Year ──
        fiscal_year, _ = FiscalYear.objects.get_or_create(
            farm=farm, year=2026,
            defaults={'start_date': date(2026, 1, 1), 'end_date': date(2026, 12, 31), 'is_closed': False}
        )
        for month in range(1, 13):
            start = date(2026, month, 1)
            end = date(2026, 12, 31) if month == 12 else date(2026, month + 1, 1) - timedelta(days=1)
            FiscalPeriod.objects.get_or_create(
                fiscal_year=fiscal_year, month=month,
                defaults={'start_date': start, 'end_date': end, 'is_closed': False}
            )

        # ── Cost & Sector ──
        CostConfiguration.objects.get_or_create(farm=farm, defaults={'currency': 'YER', 'effective_date': date(2026, 1, 1)})
        SectorRelationship.objects.get_or_create(farm=farm, defaults={'current_balance': Decimal('0.0000'), 'allow_revenue_recycling': False})

        # ── Daily Logs + Activities ──
        iri_task = Task.objects.filter(name='ري بالغمر').first()
        tasks_for_cycle = [iri_task] if iri_task else []
        fert_task = Task.objects.filter(name='تسميد').first()
        if fert_task:
            tasks_for_cycle.append(fert_task)

        daily_logs = []
        for days_ago in range(10, 0, -1):
            log_date = date.today() - timedelta(days=days_ago)
            if log_date.weekday() >= 5:
                continue
            log = DailyLog.objects.filter(farm=farm, log_date=log_date).first()
            if not log:
                log = DailyLog.objects.create(
                    farm=farm, log_date=log_date,
                    status='approved',
                    notes=f'سجل يومي مزرعة الجروبة - {log_date}',
                    created_by=admin_user,
                    approved_by=admin_user,
                    approved_at=timezone.now(),
                )
            daily_logs.append(log)

        activities = []
        for i, log in enumerate(daily_logs[:6]):
            if not tasks_for_cycle:
                break
            task_obj = tasks_for_cycle[i % len(tasks_for_cycle)]
            activity, created = Activity.objects.get_or_create(
                log=log, task=task_obj,
                defaults={
                    'crop': mango,
                    'location': locations.get('JAR-MNG'),
                    'crop_plan': crop_plans[0],
                    'days_spent': Decimal('1.0'),
                    'cost_total': Decimal('4000.0000'),
                    'cost_labor': Decimal('2500.0000'),
                    'cost_materials': Decimal('1500.0000'),
                    'created_by': admin_user,
                    'data': {'note': f'نشاط {task_obj.name} - مزرعة الجروبة'},
                }
            )
            if created and employees:
                for emp in employees[1:3]:
                    ActivityEmployee.objects.get_or_create(
                        activity=activity, employee=emp,
                        defaults={'surrah_share': Decimal('1.00')}
                    )
            activities.append(activity)
        self._ok(f'  السجلات: {len(daily_logs)}, الأنشطة: {len(activities)}')

        # ── Harvest ──
        lot, _ = HarvestLot.objects.get_or_create(
            farm=farm, crop=mango, crop_plan=crop_plans[0],
            harvest_date=date.today() - timedelta(days=4),
            defaults={'quantity': Decimal('500'), 'grade': 'First', 'location': locations.get('JAR-MNG'), 'uom': 'kg'}
        )

        # ── Sales ──
        customer = Customer.objects.filter(name='شركة الأمانة التجارية').first()
        if customer:
            invoice, created = SalesInvoice.objects.get_or_create(
                farm=farm, customer=customer, invoice_date=date.today(),
                defaults={
                    'status': 'approved',
                    'total_amount': Decimal('75000.00'),
                    'created_by': admin_user,
                }
            )
            if created:
                seed_item = Item.objects.filter(group='Seeds').first() or Item.objects.first()
                if seed_item:
                    SalesInvoiceItem.objects.create(
                        invoice=invoice, item=seed_item,
                        description='حصاد مانجو - مزرعة الجروبة',
                        qty=Decimal('500'), unit_price=Decimal('150.00'),
                        total=Decimal('75000.00'), harvest_lot=lot,
                    )
        self._ok('  فاتورة مبيعات: 1')
        return farm

    def _resolve_default_password(self, options):
        explicit = (options or {}).get('default_password')
        env_value = os.getenv('AGRIASSET_SEED_DEFAULT_PASSWORD')
        password = explicit or env_value
        if password:
            return password
        generated = get_random_string(16)
        self.stdout.write(self.style.WARNING(
            f'AGRIASSET_SEED_DEFAULT_PASSWORD not provided; generated temporary seed password: {generated}'
        ))
        return generated

    # ═══════════════════════════════════════════════════════════
    # USERS & PERMISSIONS
    # ═══════════════════════════════════════════════════════════
    def _create_users(self, farm_map):
        from smart_agri.accounts.models import FarmMembership

        for user_def in USER_DEFINITIONS:
            user, created = User.objects.get_or_create(
                username=user_def['username'],
                defaults={
                    'first_name': user_def['first_name'],
                    'last_name': user_def['last_name'],
                    'email': user_def.get('email', ''),
                    'is_staff': user_def.get('is_staff', False),
                }
            )
            if created:
                user.set_password(self.default_password)
                user.save()

            # Assign group
            group = Group.objects.filter(name=user_def['group']).first()
            if group:
                user.groups.add(group)

            # Assign farm memberships
            for farm_key in user_def.get('farms', []):
                farm = farm_map.get(farm_key)
                if farm:
                    FarmMembership.objects.get_or_create(
                        user=user, farm=farm,
                        defaults={'role': user_def.get('membership_role', 'Viewer')}
                    )

            status = 'جديد' if created else 'موجود'
            self._ok(f'  {user_def["first_name"]} {user_def["last_name"]} ({user_def["username"]}) → {user_def["group"]} [{status}]')

        # Ensure ibrahim superuser exists
        ibrahim, created = User.objects.get_or_create(
            username='ibrahim',
            defaults={
                'first_name': 'إبراهيم',
                'last_name': 'المدير العام',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            ibrahim.set_password(self.default_password)
            ibrahim.save()
            self._ok('  إبراهيم (ibrahim) → مدير النظام [جديد]')
        else:
            # Ensure existing ibrahim is superuser
            if not ibrahim.is_superuser:
                ibrahim.is_superuser = True
                ibrahim.is_staff = True
                ibrahim.save()
            self._ok('  إبراهيم (ibrahim) → مدير النظام [موجود]')

        # Assign ibrahim to all farms
        from smart_agri.accounts.models import FarmMembership
        for farm_key, farm in farm_map.items():
            if farm:
                FarmMembership.objects.get_or_create(
                    user=ibrahim, farm=farm,
                    defaults={'role': 'Admin'}
                )

    # ═══════════════════════════════════════════════════════════
    # CLEANUP
    # ═══════════════════════════════════════════════════════════
    def _clean_stale_farms(self):
        from smart_agri.core.models import Farm
        keep_slugs = ['sardud']
        stale_farms = Farm.objects.exclude(slug__in=keep_slugs)
        count = stale_farms.count()
        if count > 0:
            self._warn(f'تنظيف {count} مزرعة غير مطلوبة...')
            for farm in stale_farms:
                try:
                    farm.delete()
                    self._log(f'  حُذفت: {farm.name}')
                except Exception as e:
                    logger.exception(f"Failed to delete {farm.name}")
                    self._warn(f'  تعذر حذف {farm.name}: {e}')
        else:
            self._log('  لا توجد مزارع لتنظيفها')

    # ═══════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════
    def _print_final_summary(self, golden, sardud, jaruba):
        from smart_agri.core.models import Farm, Location, Employee, DailyLog, Activity, CropPlan, HarvestLot
        from smart_agri.inventory.models import ItemInventory
        from smart_agri.finance.models import FiscalYear, FinancialLedger
        from smart_agri.sales.models import SalesInvoice
        from smart_agri.accounts.models import FarmMembership

        self.stdout.write('\n' + '═' * 70)
        self.stdout.write(self.style.SUCCESS('📊 ملخص بذر النظام الشامل'))
        self.stdout.write('═' * 70)

        for label, farm in [('🏆 المزرعة الذهبية', golden), ('🌴 مزرعة سردود', sardud), ('🌿 مزرعة الجروبة', jaruba)]:
            if not farm:
                continue
            try:
                self.stdout.write(f'\n{label}: {farm.name}')
                self.stdout.write(f'  المواقع: {Location.objects.filter(farm=farm).count()}')
                self.stdout.write(f'  الموظفون: {Employee.objects.filter(farm=farm).count()}')
                self.stdout.write(f'  خطط المحاصيل: {CropPlan.objects.filter(farm=farm).count()}')
                self.stdout.write(f'  السجلات اليومية: {DailyLog.objects.filter(farm=farm).count()}')
                self.stdout.write(f'  الأنشطة: {Activity.objects.filter(log__farm=farm).count()}')
                self.stdout.write(f'  دفعات الحصاد: {HarvestLot.objects.filter(farm=farm).count()}')
                self.stdout.write(f'  فواتير المبيعات: {SalesInvoice.objects.filter(farm=farm).count()}')
            except Exception as e:
                logger.exception("Failed logging summary for farm")
                self._warn(f'  خطط في الملخص: {e}')

        self.stdout.write(f'\n👥 المستخدمون: {User.objects.count()}')
        self.stdout.write(f'🔑 العضويات: {FarmMembership.objects.count()}')
        self.stdout.write('═' * 70)
        self.stdout.write(self.style.SUCCESS('\n✅ تم بذر النظام بنجاح!'))
        self.stdout.write(self.style.WARNING(f'📝 كلمة المرور للمستخدمين التجريبيين: {self.default_password}'))

    # ═══════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════
    def _header(self, msg):
        self.stdout.write('\n' + '═' * 70)
        self.stdout.write(self.style.WARNING(msg))
        self.stdout.write('═' * 70)

    def _phase(self, msg):
        self.stdout.write(self.style.HTTP_INFO(f'\n{msg}'))

    def _ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f'  ✓ {msg}'))

    def _warn(self, msg):
        self.stdout.write(self.style.WARNING(f'  ⚠ {msg}'))

    def _log(self, msg):
        if self.verbose:
            self.stdout.write(f'  → {msg}')
