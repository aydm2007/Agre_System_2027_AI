"""
[AGRI-GUARDIAN] Seed Saradud Farm — Full Documentary Cycle.

Creates complete test data for مزرعة سردود on Location 3,
covering ALL financial, technical, and administrative modules
for both perennial (Mango) and seasonal (Wheat) crops.

Usage: python manage.py seed_saradud_documentary_cycle
"""
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

ZERO = Decimal("0.0000")
User = get_user_model()


class Command(BaseCommand):
    help = "بذر مزرعة سردود + دورة مستندية كاملة (الموقع 3)"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("═" * 60))
        self.stdout.write(self.style.SUCCESS("  🌾 مزرعة سردود — الدورة المستندية الشاملة (الموقع 3)"))
        self.stdout.write(self.style.SUCCESS("═" * 60))

        user = self._seed_user()
        farm = self._seed_farm()
        loc_main, loc2, loc3 = self._seed_locations(farm)
        fy, march_period = self._seed_fiscal(farm)
        self._seed_irrigation_policy(loc3)
        crops = self._seed_crops()
        items = self._seed_items(farm, loc_main)
        employees = self._seed_employees(farm)
        wheat_plan = self._seed_crop_plan_wheat(farm, loc3, crops, items)
        mango_plan = self._seed_crop_plan_mango(farm, loc3, crops)
        self._seed_activities(farm, wheat_plan, employees, items, user)
        self._seed_mango_activities(farm, mango_plan, employees, items, user)
        self._seed_ledger_entries(farm, wheat_plan, user)
        self._seed_biological_assets(farm, loc3, crops)
        self._seed_harvest(farm, wheat_plan, loc3, crops, user)
        self._seed_payroll(farm, employees, march_period, user)
        self._seed_sales(farm, user)
        self._seed_actual_expenses(farm, wheat_plan, march_period, user)
        self._seed_variance_alerts(farm, wheat_plan, mango_plan, user)
        self._seed_farm_membership(farm, user)
        self._print_summary(farm, fy, wheat_plan, mango_plan, user)

    # ═══════════════════════════════════════════════════════════
    # 1. USER
    # ═══════════════════════════════════════════════════════════
    def _seed_user(self):
        user, created = User.objects.get_or_create(
            username='saradud_admin',
            defaults={
                'email': 'admin@saradud.ye',
                'is_staff': True, 'is_superuser': True,
                'first_name': 'محمد', 'last_name': 'السردودي',
            }
        )
        if not user.has_usable_password():
            user.set_password('Saradud2026!')
            user.save()
        self.stdout.write(f"  ✅ المستخدم: {user.username} (ID={user.id})")
        return user

    # ═══════════════════════════════════════════════════════════
    # 2. FARM
    # ═══════════════════════════════════════════════════════════
    def _seed_farm(self):
        from smart_agri.core.models.farm import Farm
        farm, _ = Farm.objects.get_or_create(
            name='مزرعة سردود',
            defaults={
                'slug': 'saradud-001',
                'area': Decimal('45.00'),
                'region': 'صعدة',
                'zakat_rule': '5_PERCENT',
            }
        )
        # [Forensic Resilience] Undelete if exists but marked as deleted
        if getattr(farm, 'deleted_at', None):
            farm.deleted_at = None
            farm.is_active = True
            farm.save()
            
        farm.save()  # trigger auto-tier
        self.stdout.write(f"  ✅ المزرعة: {farm.name} (ID={farm.id}, Tier={farm.tier})")
        return farm

    # ═══════════════════════════════════════════════════════════
    # 3. LOCATIONS (3 locations including target Location 3)
    # ═══════════════════════════════════════════════════════════
    def _seed_locations(self, farm):
        from smart_agri.core.models.farm import Location
        loc_main, _ = Location.objects.get_or_create(
            farm=farm, name='القسم الرئيسي',
            defaults={'type': 'Field', 'code': 'SEC-01'}
        )
        loc2, _ = Location.objects.get_or_create(
            farm=farm, name='بستان سردود',
            defaults={'type': 'Orchard', 'code': 'SEC-02'}
        )
        loc3, _ = Location.objects.get_or_create(
            farm=farm, name='الشعبة الغربية',
            defaults={'type': 'Mixed', 'code': 'SEC-03'}
        )
        self.stdout.write(
            f"  ✅ المواقع: {loc_main.name} (1), {loc2.name} (2), {loc3.name} (3)"
        )
        self.stdout.write(f"     📍 الدورة المستندية ← الموقع 3: {loc3.name}")
        return loc_main, loc2, loc3

    # ═══════════════════════════════════════════════════════════
    # 3.1 IRRIGATION POLICY (Zakat Gate — Axis 9)
    # ═══════════════════════════════════════════════════════════
    def _seed_irrigation_policy(self, loc3):
        from smart_agri.core.models.farm import LocationIrrigationPolicy
        from django.contrib.postgres.fields import DateRangeField  # noqa: F401
        try:
            from psycopg2.extras import DateRange
        except ImportError:
            from django.db.backends.postgresql.psycopg_any import DateRange

        policy, created = LocationIrrigationPolicy.objects.get_or_create(
            location=loc3,
            zakat_rule=LocationIrrigationPolicy.ZAKAT_WELL_5,
            is_active=True,
            defaults={
                'valid_daterange': DateRange(date(2026, 1, 1), date(2026, 12, 31)),
                'reason': 'ري بالتنقيط — آبار ارتوازية',
                'approved_by': None,
            }
        )
        label = 'جديدة' if created else 'موجودة'
        self.stdout.write(
            f"  ✅ سياسة الري: {loc3.name} → WELL_5 (5% زكاة) [{label}]"
        )

    # ═══════════════════════════════════════════════════════════
    # 4. FISCAL YEAR + 12 PERIODS
    # ═══════════════════════════════════════════════════════════
    def _seed_fiscal(self, farm):
        from smart_agri.finance.models import FiscalYear, FiscalPeriod
        fy, _ = FiscalYear.objects.get_or_create(
            year=2026, farm=farm,
            defaults={'start_date': date(2026, 1, 1), 'end_date': date(2026, 12, 31), 'is_active': True}
        )
        for m in range(1, 13):
            m_start = date(2026, m, 1)
            m_end = date(2026, m + 1, 1) - timedelta(days=1) if m < 12 else date(2026, 12, 31)
            FiscalPeriod.objects.get_or_create(
                fiscal_year=fy, month=m,
                defaults={
                    'start_date': m_start, 'end_date': m_end,
                    'status': 'open' if m >= 3 else 'hard_close',
                }
            )
        march = FiscalPeriod.objects.get(fiscal_year=fy, month=3)
        self.stdout.write(f"  ✅ السنة المالية: {fy.year} | مارس={march.status}")
        return fy, march

    # ═══════════════════════════════════════════════════════════
    # 5. CROPS
    # ═══════════════════════════════════════════════════════════
    def _seed_crops(self):
        from smart_agri.core.models.crop import Crop, CropVariety, CropProduct
        wheat, _ = Crop.objects.get_or_create(
            name='قمح', defaults={'mode': 'Open', 'is_perennial': False}
        )
        mango, _ = Crop.objects.get_or_create(
            name='مانجو', defaults={'mode': 'Open', 'is_perennial': True}
        )
        v_wheat, _ = CropVariety.objects.get_or_create(
            crop=wheat, name='بلدي', defaults={'est_days_to_harvest': 120}
        )
        v_mango, _ = CropVariety.objects.get_or_create(
            crop=mango, name='سكري', defaults={'est_days_to_harvest': 365}
        )
        CropProduct.objects.get_or_create(
            crop=wheat, name='حبوب قمح',
            defaults={'pack_uom': 'كيلو', 'is_primary': True}
        )
        CropProduct.objects.get_or_create(
            crop=mango, name='فاكهة مانجو',
            defaults={'pack_uom': 'كيلو', 'is_primary': True}
        )
        self.stdout.write(f"  ✅ المحاصيل: {wheat.name}, {mango.name}")
        return {'wheat': wheat, 'mango': mango, 'v_wheat': v_wheat, 'v_mango': v_mango}

    # ═══════════════════════════════════════════════════════════
    # 6. ITEMS + INVENTORY
    # ═══════════════════════════════════════════════════════════
    def _seed_items(self, farm, location):
        from smart_agri.inventory.models import Item, ItemInventory, Unit
        kg, _ = Unit.objects.get_or_create(code='KG', defaults={'name': 'كيلوغرام', 'symbol': 'كغ', 'category': Unit.CATEGORY_MASS})
        ltr, _ = Unit.objects.get_or_create(code='LTR', defaults={'name': 'لتر', 'symbol': 'لتر', 'category': Unit.CATEGORY_VOLUME})

        defs = [
            ('سماد يوريا',  'FERT-001', 'FERTILIZER', kg,  Decimal('150.0000'), 500),
            ('ديزل',        'FUEL-001', 'FUEL',       ltr, Decimal('200.0000'), 1000),
            ('مبيد حشري',   'PEST-001', 'PESTICIDE',  ltr, Decimal('500.0000'), 200),
            ('بذور قمح',    'SEED-001', 'SEED',       kg,  Decimal('300.0000'), 200),
            ('أكياس تعبئة', 'PACK-001', 'PACKAGING',  kg,  Decimal('50.0000'),  300),
        ]
        items = {}
        for name, sku, cat, unit, cost, qty in defs:
            item, _ = Item.objects.get_or_create(
                name=name, defaults={'group': cat, 'unit': unit, 'unit_price': cost, 'reorder_level': Decimal('10.0000')}
            )
            ItemInventory.objects.get_or_create(
                item=item, farm=farm, location=location,
                defaults={'qty': Decimal(str(qty))}
            )
            items[sku] = item
        self.stdout.write(f"  ✅ المخزون: {len(items)} أصناف")
        return items

    # ═══════════════════════════════════════════════════════════
    # 7. EMPLOYEES
    # ═══════════════════════════════════════════════════════════
    def _seed_employees(self, farm):
        from smart_agri.core.models.hr import Employee
        from smart_agri.core.models.settings import LaborRate
        emps = []
        defs = [
            ('EMP-001', 'أحمد', 'المشرف',  'OFFICIAL', 'SUPERVISOR', Decimal('5000.0000')),
            ('EMP-002', 'علي', 'العامل',   'CASUAL',   'WORKER',     Decimal('2000.0000')),
            ('EMP-003', 'محمد', 'الحارث',  'CASUAL',   'WORKER',     Decimal('2000.0000')),
            ('EMP-004', 'سالم', 'السائق',  'OFFICIAL', 'DRIVER',     Decimal('3500.0000')),
        ]
        for emp_id, first, last, cat, role, rate in defs:
            defaults = {'category': cat, 'role': role, 'first_name': first, 'last_name': last}
            if cat == 'OFFICIAL':
                defaults['base_salary'] = rate
            else:
                defaults['shift_rate'] = rate
            
            emp, _ = Employee.objects.get_or_create(
                employee_id=emp_id, farm=farm,
                defaults=defaults
            )
            emps.append(emp)
        
        LaborRate.objects.get_or_create(farm=farm, role_name='WORKER', defaults={'daily_rate': Decimal('2000.0000'), 'cost_per_hour': Decimal('250.0000')})
        LaborRate.objects.get_or_create(farm=farm, role_name='DRIVER', defaults={'daily_rate': Decimal('3500.0000'), 'cost_per_hour': Decimal('437.5000')})

        self.stdout.write(f"  ✅ الموظفين والعمالة: {len(emps)} موظفين، 2 أسعار عمالة")
        return emps

    # ═══════════════════════════════════════════════════════════
    # 8. CROP PLAN — WHEAT (Seasonal) on Location 3
    # ═══════════════════════════════════════════════════════════
    def _seed_crop_plan_wheat(self, farm, loc3, crops, items):
        from smart_agri.core.models.planning import CropPlan, Season, CropPlanBudgetLine, CropPlanLocation
        season, _ = Season.objects.get_or_create(
            name='ربيع 2026',
            defaults={'start_date': date(2026, 3, 1), 'end_date': date(2026, 6, 30)}
        )
        plan, _ = CropPlan.objects.get_or_create(
            name='قمح سردود — الموقع 3 — ربيع 2026',
            farm=farm,
            defaults={
                'crop': crops['wheat'],
                'season': season,
                'start_date': date(2026, 3, 1),
                'end_date': date(2026, 6, 30),
                'expected_yield': Decimal('5000.0000'),
                'budget_materials': Decimal('50000.0000'),
                'budget_labor': Decimal('30000.0000'),
                'budget_machinery': Decimal('10000.0000'),
                'status': 'active',
            }
        )
        CropPlanLocation.objects.get_or_create(crop_plan=plan, location=loc3)
        budget_defs = [
            ('materials', Decimal('50000.0000')),
            ('labor',     Decimal('30000.0000')),
            ('machinery', Decimal('10000.0000')),
            ('other',     Decimal('5000.0000')),
        ]
        for cat, amount in budget_defs:
            CropPlanBudgetLine.objects.get_or_create(
                crop_plan=plan, category=cat,
                defaults={'total_budget': amount}
            )
        self.stdout.write(f"  ✅ خطة القمح: {plan.name} (ID={plan.id})")
        return plan

    # ═══════════════════════════════════════════════════════════
    # 8.1 CROP PLAN — MANGO (Perennial) on Location 3
    # ═══════════════════════════════════════════════════════════
    def _seed_crop_plan_mango(self, farm, loc3, crops):
        from smart_agri.core.models.planning import CropPlan, Season, CropPlanBudgetLine, CropPlanLocation
        season, _ = Season.objects.get_or_create(
            name='ربيع 2026',
            defaults={'start_date': date(2026, 3, 1), 'end_date': date(2026, 6, 30)}
        )
        plan, _ = CropPlan.objects.get_or_create(
            name='مانجو سردود — الموقع 3 — 2026',
            farm=farm,
            defaults={
                'crop': crops['mango'],
                'season': season,
                'start_date': date(2026, 1, 1),
                'end_date': date(2026, 12, 31),
                'expected_yield': Decimal('3000.0000'),
                'budget_materials': Decimal('40000.0000'),
                'budget_labor': Decimal('25000.0000'),
                'budget_machinery': Decimal('8000.0000'),
                'status': 'active',
            }
        )
        CropPlanLocation.objects.get_or_create(crop_plan=plan, location=loc3)
        budget_defs = [
            ('materials', Decimal('40000.0000')),
            ('labor',     Decimal('25000.0000')),
            ('machinery', Decimal('8000.0000')),
            ('other',     Decimal('4000.0000')),
        ]
        for cat, amount in budget_defs:
            CropPlanBudgetLine.objects.get_or_create(
                crop_plan=plan, category=cat,
                defaults={'total_budget': amount}
            )
        self.stdout.write(f"  ✅ خطة المانجو: {plan.name} (ID={plan.id})")
        return plan

    # ═══════════════════════════════════════════════════════════
    # 9. DAILY LOG + ACTIVITIES (Wheat — Seasonal)
    # ═══════════════════════════════════════════════════════════
    def _seed_activities(self, farm, plan, employees, items, user):
        from smart_agri.core.models.log import DailyLog
        from smart_agri.core.models.activity import Activity, ActivityItem, ActivityEmployee
        from smart_agri.core.models.settings import Supervisor

        emp = employees[0]
        supervisor, _ = Supervisor.objects.get_or_create(
            farm=farm, code=emp.employee_id,
            defaults={'name': f"{emp.first_name} {emp.last_name}"}
        )

        # [V21 Forensic Hardening] Seed Custody for Supervisor to allow consumption
        from smart_agri.core.services.custody_transfer_service import CustodyTransferService
        from smart_agri.core.models.farm import Location
        # Identify source location (Main Warehouse or first available)
        source_loc = Location.objects.filter(farm=farm, type='Warehouse').first() or \
                     Location.objects.filter(farm=farm, type='Main').first() or \
                     Location.objects.filter(farm=farm).first()
        
        for item in items.values():
            try:
                transfer = CustodyTransferService.issue_transfer(
                    farm=farm, supervisor=supervisor, item=item,
                    source_location=source_loc, qty=Decimal("100.0000"),
                    actor=user, allow_top_up=True,
                    idempotency_key=f"seed-custody-{supervisor.id}-{item.id}"
                )
                CustodyTransferService.accept_transfer(transfer=transfer, actor=user)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  ⚠️ Custody seeding skipped for {item.name}: {str(e)}"))

        for day_offset, tasks in [
            (0,  [('PLANTING',    'زراعة بذور القمح — الموقع 3',  'SEED-001', Decimal('30.0000'))]),
            (3,  [('IRRIGATION',  'ري بالتنقيط — الموقع 3',       None,        ZERO),
                  ('FERTILIZING', 'تسميد يوريا — الموقع 3',       'FERT-001', Decimal('25.0000'))]),
            (7,  [('SPRAYING',    'رش مبيد حشري — الموقع 3',      'PEST-001', Decimal('5.0000'))]),
        ]:
            log_date = date(2026, 3, 1) + timedelta(days=day_offset)
            log, _ = DailyLog.objects.get_or_create(
                farm=farm, log_date=log_date,
                defaults={'created_by': user, 'supervisor': supervisor}
            )
            for task_type, notes, item_sku, item_qty in tasks:
                from smart_agri.core.models.task import Task
                arch_map = {
                    'PLANTING': Task.Archetype.GENERAL,
                    'IRRIGATION': Task.Archetype.IRRIGATION,
                    'FERTILIZING': Task.Archetype.MATERIAL_INTENSIVE,
                    'SPRAYING': Task.Archetype.MATERIAL_INTENSIVE,
                }
                actual_task, _ = Task.objects.get_or_create(
                    crop=plan.crop, name=task_type,
                    defaults={'stage': 'General', 'archetype': arch_map.get(task_type, Task.Archetype.GENERAL)}
                )

                activity, act_created = Activity.objects.get_or_create(
                    log=log, task=actual_task, crop_plan=plan,
                )
                if act_created and notes:
                    activity.note = notes
                    activity.save()
                if act_created:
                    # Assign 2 workers
                    for emp in employees[:2]:
                        ActivityEmployee.objects.get_or_create(
                            activity=activity, employee=emp,
                            defaults={'labor_type': 'REGISTERED', 'surrah_share': Decimal('1.00')}
                        )
                    # Assign material if applicable
                    if item_sku and item_sku in items:
                        item = items[item_sku]
                        ActivityItem.objects.get_or_create(
                            activity=activity, item=item,
                            defaults={
                                'qty': item_qty,
                                'cost_per_unit': item.unit_price,
                                'uom': 'كغ' if item_sku != 'PEST-001' else 'لتر',
                            }
                        )
        self.stdout.write("  ✅ أنشطة القمح: 3 سجلات × أنشطة + عمالة + مواد")

    # ═══════════════════════════════════════════════════════════
    # 9.1 DAILY LOG + ACTIVITIES (Mango — Perennial)
    # ═══════════════════════════════════════════════════════════
    def _seed_mango_activities(self, farm, mango_plan, employees, items, user):
        from smart_agri.core.models.log import DailyLog
        from smart_agri.core.models.activity import Activity, ActivityItem, ActivityEmployee
        from smart_agri.core.models.settings import Supervisor

        emp = employees[0]
        supervisor, _ = Supervisor.objects.get_or_create(
            farm=farm, code=emp.employee_id,
            defaults={'name': f"{emp.first_name} {emp.last_name}"}
        )

        for day_offset, tasks in [
            (1,  [('PRUNING',     'تقليم أشجار المانجو — الموقع 3', None, ZERO)]),
            (5,  [('FERTILIZING', 'تسميد أشجار المانجو — الموقع 3', 'FERT-001', Decimal('20.0000'))]),
            (9,  [('SPRAYING',    'رش وقائي للمانجو — الموقع 3',    'PEST-001', Decimal('3.0000'))]),
        ]:
            log_date = date(2026, 3, 1) + timedelta(days=day_offset)
            log, _ = DailyLog.objects.get_or_create(
                farm=farm, log_date=log_date,
                defaults={'created_by': user, 'supervisor': supervisor}
            )
            for task_type, notes, item_sku, item_qty in tasks:
                from smart_agri.core.models.task import Task
                arch_map = {
                    'PRUNING': Task.Archetype.PERENNIAL_SERVICE,
                    'FERTILIZING': Task.Archetype.MATERIAL_INTENSIVE,
                    'SPRAYING': Task.Archetype.MATERIAL_INTENSIVE,
                }
                actual_task, _ = Task.objects.get_or_create(
                    crop=mango_plan.crop, name=task_type,
                    defaults={'stage': 'General', 'archetype': arch_map.get(task_type, Task.Archetype.GENERAL)}
                )

                activity, act_created = Activity.objects.get_or_create(
                    log=log, task=actual_task, crop_plan=mango_plan,
                )
                if act_created and notes:
                    activity.note = notes
                    activity.save()
                if act_created:
                    for emp in employees[1:3]:
                        ActivityEmployee.objects.get_or_create(
                            activity=activity, employee=emp,
                            defaults={'labor_type': 'REGISTERED', 'surrah_share': Decimal('1.00')}
                        )
                    if item_sku and item_sku in items:
                        item = items[item_sku]
                        ActivityItem.objects.get_or_create(
                            activity=activity, item=item,
                            defaults={
                                'qty': item_qty,
                                'cost_per_unit': item.unit_price,
                                'uom': 'لتر' if item_sku == 'PEST-001' else 'كغ',
                            }
                        )
        self.stdout.write("  ✅ أنشطة المانجو: 3 سجلات (تقليم + تسميد + رش)")

    # ═══════════════════════════════════════════════════════════
    # 10. LEDGER ENTRIES (double-entry)
    # ═══════════════════════════════════════════════════════════
    def _seed_ledger_entries(self, farm, plan, user):
        from smart_agri.finance.models import FinancialLedger as FL
        entries = [
            ('1400-WIP',       Decimal('9000.0000'), ZERO,                  'بذور قمح → WIP'),
            ('1300-INV-ASSET', ZERO,                 Decimal('9000.0000'),  'صرف بذور'),
            ('1400-WIP',       Decimal('4200.0000'), ZERO,                  'سماد يوريا → WIP'),
            ('1300-INV-ASSET', ZERO,                 Decimal('4200.0000'),  'صرف سماد'),
            ('1400-WIP',       Decimal('2750.0000'), ZERO,                  'مبيد حشري → WIP'),
            ('1300-INV-ASSET', ZERO,                 Decimal('2750.0000'),  'صرف مبيد'),
            ('1400-WIP',       Decimal('12000.0000'), ZERO,                 'عمالة → WIP'),
            ('2000-PAY-SAL',   ZERO,                 Decimal('12000.0000'), 'مستحقات عمالة'),
            ('1400-WIP',       Decimal('4000.0000'), ZERO,                  'ديزل ري → WIP'),
            ('1300-INV-ASSET', ZERO,                 Decimal('4000.0000'),  'صرف ديزل'),
            ('1400-WIP',       Decimal('1500.0000'), ZERO,                  'overhead → WIP'),
            ('4000-OVERHEAD',  ZERO,                 Decimal('1500.0000'),  'تخصيص overhead'),
        ]
        total_dr = ZERO
        total_cr = ZERO
        for code, dr, cr, desc in entries:
            FL.objects.get_or_create(
                farm=farm, account_code=code,
                description=f'{desc} — سردود',
                crop_plan=plan,
                defaults={'debit': dr, 'credit': cr, 'created_by': user}
            )
            total_dr += dr
            total_cr += cr
        balanced = '✅ متوازن' if total_dr == total_cr else '❌ غير متوازن'
        self.stdout.write(f"  ✅ القيود: {len(entries)} | DR {total_dr} / CR {total_cr} {balanced}")

    # ═══════════════════════════════════════════════════════════
    # 11. BIOLOGICAL ASSETS (Mango on Location 3)
    # ═══════════════════════════════════════════════════════════
    def _seed_biological_assets(self, farm, loc3, crops):
        from smart_agri.core.models.inventory import BiologicalAssetCohort
        cohort, _ = BiologicalAssetCohort.objects.get_or_create(
            farm=farm, batch_name='دفعة مانجو سردود 2020',
            defaults={
                'crop': crops['mango'],
                'variety': crops['v_mango'],
                'location': loc3,
                'planted_date': date(2020, 1, 1),
                'quantity': 150,
                'status': 'PRODUCTIVE',
                'capitalized_cost': Decimal('750000.0000'),
                'useful_life_years': 25,
            }
        )
        self.stdout.write(f"  ✅ أصول بيولوجية: {cohort.batch_name} ({cohort.quantity} شجرة)")

    # ═══════════════════════════════════════════════════════════
    # 12. HARVEST
    # ═══════════════════════════════════════════════════════════
    def _seed_harvest(self, farm, plan, loc3, crops, user):
        from smart_agri.core.models.log import DailyLog
        from smart_agri.core.models.activity import Activity, ActivityHarvest
        from smart_agri.core.models.inventory import HarvestLot

        harvest_date = date(2026, 3, 20)
        log, _ = DailyLog.objects.get_or_create(
            farm=farm, log_date=harvest_date,
            defaults={'created_by': user}
        )
        from smart_agri.core.models.task import Task
        actual_task, _ = Task.objects.get_or_create(
            crop=plan.crop, name='HARVEST',
            defaults={'stage': 'Harvest', 'archetype': Task.Archetype.HARVEST}
        )
        act, act_created = Activity.objects.get_or_create(
            log=log, task=actual_task, crop_plan=plan
        )
        if act_created:
            act.note = 'حصاد قمح — الموقع 3'
            act.save()
        ActivityHarvest.objects.get_or_create(
            activity=act,
            defaults={
                'harvest_quantity': Decimal('4800.000'),
                'uom': 'كيلو',
            }
        )
        HarvestLot.objects.get_or_create(
            farm=farm, crop=crops['wheat'],
            harvest_date=harvest_date,
            defaults={
                'crop_plan': plan,
                'location': loc3,
                'quantity': Decimal('4800.000'),
                'grade': 'First',
                'uom': 'kg',
            }
        )
        # [AGRI-GUARDIAN §Axis-7] Harvest AuditLog
        try:
            from smart_agri.core.models.log import AuditLog
            AuditLog.objects.get_or_create(
                action='HARVEST',
                object_id=str(act.pk),
                defaults={
                    'model': 'Activity',
                    'actor': user,
                    'new_payload': {
                        'quantity': '4800',
                        'crop': 'قمح',
                        'location': 'الموقع 3',
                        'farm_id': farm.pk,
                    },
                }
            )
        except Exception as e:
            logger.warning("Harvest AuditLog seeding failed: %s", e)

        self.stdout.write("  ✅ الحصاد: 4,800 كغ قمح درجة أولى + AuditLog")

    # ═══════════════════════════════════════════════════════════
    # 13. PAYROLL
    # ═══════════════════════════════════════════════════════════
    def _seed_payroll(self, farm, employees, period, user):
        from smart_agri.core.models.hr import PayrollRun, PayrollSlip, PayrollStatus

        run, created = PayrollRun.objects.get_or_create(
            farm=farm,
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            defaults={
                'status': PayrollStatus.APPROVED,
                'total_amount': Decimal('24500.0000'),
                'created_by': user,
            }
        )
        if created:
            for emp in employees:
                days = Decimal('20') if emp.category == 'OFFICIAL' else Decimal('15')
                basic = emp.base_salary * days
                PayrollSlip.objects.get_or_create(
                    run=run, employee=emp,
                    defaults={
                        'basic_amount': basic,
                        'allowances_amount': ZERO,
                        'overtime_amount': ZERO,
                        'deductions_amount': ZERO,
                        'net_pay': basic,
                        'days_worked': days,
                    }
                )
        self.stdout.write(f"  ✅ كشف الرواتب: مارس 2026 | {run.total_amount} ر.ي")

    # ═══════════════════════════════════════════════════════════
    # 14. SALES
    # ═══════════════════════════════════════════════════════════
    def _seed_sales(self, farm, user):
        from smart_agri.sales.models import Customer, SalesInvoice, SalesInvoiceItem

        customer, _ = Customer.objects.get_or_create(
            name='تاجر الحبوب — صنعاء',
            defaults={'phone': '777-123-456', 'is_active': True}
        )
        inv1, c1 = SalesInvoice.objects.get_or_create(
            farm=farm, customer=customer, invoice_date=date(2026, 3, 21),
            defaults={'status': 'draft', 'created_by': user}
        )
        from smart_agri.inventory.models import Item, Unit
        kg, _ = Unit.objects.get_or_create(code='KG', defaults={'name': 'كيلوغرام', 'symbol': 'كغ', 'category': Unit.CATEGORY_MASS})
        wheat_item, _ = Item.objects.get_or_create(
            name='حبوب قمح (حصاد)',
            defaults={'group': 'PRODUCT', 'unit': kg, 'unit_price': Decimal('40.0000')}
        )
        if c1:
            SalesInvoiceItem.objects.create(
                invoice=inv1, item=wheat_item, description='حبوب قمح',
                qty=Decimal('2000.0000'), unit_price=Decimal('40.0000'),
            )
        inv2, c2 = SalesInvoice.objects.get_or_create(
            farm=farm, customer=customer, invoice_date=date(2026, 3, 21),
            defaults={'status': 'draft', 'created_by': user}
        )
        if c2:
            SalesInvoiceItem.objects.create(
                invoice=inv2, item=wheat_item, description='حبوب قمح',
                qty=Decimal('2800.0000'), unit_price=Decimal('38.0000'),
            )
        self.stdout.write("  ✅ المبيعات: INV-001 (80,000) + INV-002 (106,400)")

    # ═══════════════════════════════════════════════════════════
    # 15. ACTUAL EXPENSES
    # ═══════════════════════════════════════════════════════════
    def _seed_actual_expenses(self, farm, plan, period, user):
        from smart_agri.finance.models import ActualExpense
        defs = [
            ('مواد زراعية', '2000-MATERIAL', Decimal('13200.0000')),
            ('عمالة',       '1000-LABOR',    Decimal('12000.0000')),
            ('محروقات',     '3000-MACHINERY',Decimal('4000.0000')),
            ('مبيدات',      '2000-MATERIAL', Decimal('2750.0000')),
            ('أكياس تعبئة', '2000-MATERIAL', Decimal('1500.0000')),
        ]
        total = ZERO
        for desc, code, amount in defs:
            ActualExpense.objects.get_or_create(
                farm=farm, description=f'{desc} — سردود',
                defaults={
                    'account_code': code, 
                    'period_start': date(2026, 3, 1),
                    'period_end': date(2026, 3, 31),
                    'amount': amount,
                    'date': date(2026, 3, 20),
                }
            )
            total += amount
        self.stdout.write(f"  ✅ المصروفات: {len(defs)} بنود | {total} ر.ي")

    # ═══════════════════════════════════════════════════════════
    # 15.1 VARIANCE ALERTS (Axis 8 + 14)
    # ═══════════════════════════════════════════════════════════
    def _seed_variance_alerts(self, farm, wheat_plan, mango_plan, user):
        from smart_agri.core.models.report import VarianceAlert

        alerts_defs = [
            # Budget overrun alert
            {
                'category': VarianceAlert.CATEGORY_BUDGET_OVERRUN,
                'activity_name': 'تسميد يوريا — قمح',
                'planned_cost': Decimal('3750.0000'),
                'actual_cost': Decimal('4200.0000'),
                'variance_amount': Decimal('450.0000'),
                'variance_percentage': Decimal('12.00'),
                'alert_message': '⚠️ تنبيه رقابي: تسميد يوريا تجاوز الميزانية بنسبة 12%.',
            },
            # Schedule deviation alert
            {
                'category': VarianceAlert.CATEGORY_SCHEDULE_DEVIATION,
                'activity_name': 'رش مبيد — مانجو',
                'planned_cost': ZERO,
                'actual_cost': ZERO,
                'variance_amount': Decimal('5.0000'),
                'variance_percentage': Decimal('5.00'),
                'alert_message': '⚠️ النشاط \'رش مبيد\' أُنجز بعد نافذة الخطة بـ 5 أيام. [WARNING]',
            },
        ]
        count = 0
        for alert_def in alerts_defs:
            _, created = VarianceAlert.objects.get_or_create(
                farm=farm,
                alert_message=alert_def['alert_message'],
                defaults=alert_def,
            )
            if created:
                count += 1
        self.stdout.write(f"  ✅ تنبيهات الانحرافات: {count} جديدة (ميزانية + جدول زمني)")

    # ═══════════════════════════════════════════════════════════
    # 16. FARM MEMBERSHIP (RLS)
    # ═══════════════════════════════════════════════════════════
    def _seed_farm_membership(self, farm, user):
        from smart_agri.accounts.models import FarmMembership
        FarmMembership.objects.get_or_create(
            user=user, farm=farm,
            defaults={'role': 'مدير المزرعة'}
        )
        self.stdout.write(f"  ✅ عضوية المزرعة: {user.username} → {farm.name}")

    # ═══════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════
    def _print_summary(self, farm, fy, wheat_plan, mango_plan, user):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("═" * 60))
        self.stdout.write(self.style.SUCCESS("  ✅ الدورة المستندية جاهزة — مزرعة سردود"))
        self.stdout.write(self.style.SUCCESS("═" * 60))
        self.stdout.write(f"""
  📊 ملخص:
     🏡 المزرعة:   {farm.name} (ID={farm.id})
     👤 المستخدم:  {user.username}
     📅 السنة:     {fy.year}
     📍 الموقع:    الموقع 3 (الشعبة الغربية)
     🌾 المحاصيل:  قمح (موسمي) + مانجو (معمر)
     📦 المخزون:   5 أصناف
     👷 الموظفين:  4
     📋 خطة القمح: {wheat_plan.name}
     📋 خطة المانجو: {mango_plan.name}
     📝 الأنشطة:   زراعة + ري + تسميد + رش + تقليم (قمح + مانجو)
     💰 القيود:    DR 33,450 / CR 33,450
     🌳 أصول:      150 شجرة مانجو (PRODUCTIVE)
     🌿 الحصاد:    4,800 كغ قمح
     💳 الرواتب:   24,500 ر.ي
     🧾 المبيعات:  186,400 ر.ي
     📊 المصروفات: 33,450 ر.ي
     ⚠️ تنبيهات:   2 (ميزانية + جدول زمني)
     🕌 سياسة الري: WELL_5 (5% زكاة)

  🔧 التالي:
     python manage.py runserver
        """)
