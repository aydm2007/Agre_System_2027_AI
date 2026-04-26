"""
[AGRI-GUARDIAN] Golden Farm Seeder - Complete Test Data & Document Cycle
==========================================================================
Creates a fully operational "Golden Farm" with complete test data.
This is the REFERENCE implementation for testing and validation.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.text import slugify

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = '[AGRI-GUARDIAN] Create Golden Farm with complete test data and document cycle'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Remove existing Golden Farm data before creating',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.verbose = options.get('verbose', False)
        self.stdout.write(self.style.WARNING('\n' + '=' * 70))
        self.stdout.write(self.style.WARNING('🌾 AGRI-GUARDIAN: Golden Farm Seeder'))
        self.stdout.write(self.style.WARNING('=' * 70 + '\n'))

        if options.get('clean'):
            self._clean_golden_farm()

        # Import models dynamically to avoid import errors
        from smart_agri.core.models import Farm, Location, Asset, Employee
        from smart_agri.core.models import Crop, CropVariety, Task, Season, CropPlan, CropPlanBudgetLine
        from smart_agri.core.models import Activity, DailyLog, ActivityItem, ActivityEmployee, ActivityMachineUsage
        from smart_agri.core.models import LocationTreeStock, TreeStockEvent, TreeProductivityStatus
        from smart_agri.core.models import HarvestLot, LaborRate, MachineRate
        from smart_agri.inventory.models import Unit, Item, ItemInventory, ItemInventoryBatch
        from smart_agri.finance.models import FiscalYear, FiscalPeriod, FinancialLedger
        from smart_agri.sales.models import SalesInvoice, SalesInvoiceItem, Customer

        # Phase 1: Organization Setup
        self.stdout.write(self.style.HTTP_INFO('\n📋 Phase 1: Organization Setup'))
        
        # Create Farm
        farm_slug = 'golden-farm'
        farm, created = Farm.objects.get_or_create(
            slug=farm_slug,
            defaults={
                'name': 'المزرعة الذهبية - Golden Farm',
                'region': 'منطقة صنعاء الزراعية',
                'area': Decimal('150.00'),
                'description': 'مزرعة نموذجية متكاملة لاختبار النظام',
            }
        )
        status = 'Created' if created else 'Exists'
        self.stdout.write(self.style.SUCCESS(f'  ✓ Farm: {farm.name} ({status})'))

        # Create Admin User
        admin_user, _ = User.objects.get_or_create(
            username='golden_admin',
            defaults={
                'email': 'admin@goldenfarm.ye',
                'first_name': 'مدير',
                'last_name': 'المزرعة',
                'is_staff': True,
            }
        )
        if created:
            admin_user.set_password('GoldenFarm2026!')
            admin_user.save()
        self._log(f'Admin user: {admin_user.username}')

        # Create Locations
        locations_data = [
            {'name': 'القطاع الشمالي - Block A', 'code': 'GOLD-A', 'type': 'Field'},
            {'name': 'القطاع الجنوبي - Block B', 'code': 'GOLD-B', 'type': 'Field'},
            {'name': 'القطاع الشرقي - Block C', 'code': 'GOLD-C', 'type': 'Orchard'},
            {'name': 'القطاع الغربي - Block D', 'code': 'GOLD-D', 'type': 'Orchard'},
            {'name': 'مستودع البذور - Seed Store', 'code': 'GOLD-SEED', 'type': 'Service'},
            {'name': 'مستودع الأسمدة - Fertilizer Store', 'code': 'GOLD-FERT', 'type': 'Service'},
        ]
        
        locations = []
        for loc_data in locations_data:
            loc, _ = Location.objects.get_or_create(
                farm=farm,
                code=loc_data['code'],
                defaults=loc_data
            )
            locations.append(loc)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Locations: {len(locations)} created'))

        # Phase 2: Resource Setup
        self.stdout.write(self.style.HTTP_INFO('\n🔧 Phase 2: Resource Setup'))
        
        # Create Units
        units_data = [
            {'code': 'KG', 'name': 'كيلوغرام', 'symbol': 'kg', 'category': 'mass'},
            {'code': 'TON', 'name': 'طن', 'symbol': 'ton', 'category': 'mass'},
            {'code': 'L', 'name': 'لتر', 'symbol': 'L', 'category': 'volume'},
        ]
        for unit_data in units_data:
            Unit.objects.get_or_create(
                code=unit_data['code'],
                defaults=unit_data
            )
        self._log('Units created')

        # Create Employees
        employees_data = [
            {'first_name': 'أحمد', 'last_name': 'الحارثي', 'employee_id': 'EMP-001', 'role': 'Manager'},
            {'first_name': 'علي', 'last_name': 'العمري', 'employee_id': 'EMP-002', 'role': 'Engineer'},
            {'first_name': 'محمد', 'last_name': 'الصنعاني', 'employee_id': 'EMP-003', 'role': 'Worker'},
            {'first_name': 'عبدالرحمن', 'last_name': 'الأحمدي', 'employee_id': 'EMP-004', 'role': 'Worker'},
            {'first_name': 'يوسف', 'last_name': 'القاضي', 'employee_id': 'EMP-005', 'role': 'Worker'},
        ]
        
        employees = []
        for emp_data in employees_data:
            emp, _ = Employee.objects.get_or_create(
                farm=farm,
                employee_id=emp_data['employee_id'],
                defaults={
                    'first_name': emp_data['first_name'],
                    'last_name': emp_data['last_name'],
                    'role': emp_data['role'],
                    'is_active': True,
                    'joined_date': date(2025, 1, 1),
                }
            )
            employees.append(emp)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Employees: {len(employees)} created'))

        # Create Assets
        assets_data = [
            {'name': 'جرار جون دير 5075E', 'code': 'TRACT-001', 'category': 'Machinery'},
            {'name': 'حصادة متعددة', 'code': 'HARV-001', 'category': 'Machinery'},
            {'name': 'نظام ري بالتنقيط', 'code': 'IRR-001', 'category': 'Irrigation'},
            {'name': 'شاحنة نقل', 'code': 'TRUCK-001', 'category': 'Vehicle'},
        ]
        
        assets = []
        for asset_data in assets_data:
            asset, _ = Asset.objects.get_or_create(
                farm=farm,
                code=asset_data['code'],
                defaults={
                    'name': asset_data['name'],
                    'category': asset_data['category'],
                    'purchase_value': Decimal('100000.00'),
                }
            )
            assets.append(asset)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Assets: {len(assets)} created'))

        # Create Rates
        LaborRate.objects.update_or_create(
            farm=farm,
            role_name='عامل يومي',
            effective_date=date(2026, 1, 1),
            defaults={
                'daily_rate': Decimal('100.00'),
                'cost_per_hour': Decimal('12.50'),
                'currency': 'YER',
            }
        )
        
        for asset in Asset.objects.filter(farm=farm, category='Machinery'):
            MachineRate.objects.update_or_create(
                asset=asset,
                defaults={
                    'daily_rate': Decimal('4000.00'),
                    'cost_per_hour': Decimal('500.00'),
                    'fuel_consumption_rate': Decimal('8.5'),
                }
            )
        self._log('Rates configured')

        # Phase 3: Inventory Setup
        self.stdout.write(self.style.HTTP_INFO('\n📦 Phase 3: Inventory Setup'))
        
        kg_unit = Unit.objects.filter(code='KG').first()
        liter_unit = Unit.objects.filter(code='L').first()
        
        items_data = [
            {'name': 'بذور قمح محسنة', 'group': 'Seeds', 'unit_price': Decimal('50.00')},
            {'name': 'سماد يوريا 46%', 'group': 'Fertilizers', 'unit_price': Decimal('25.00')},
            {'name': 'سماد NPK 15-15-15', 'group': 'Fertilizers', 'unit_price': Decimal('35.00')},
            {'name': 'مبيد حشري', 'group': 'Pesticides', 'unit_price': Decimal('120.00')},
            {'name': 'ديزل', 'group': 'Fuel', 'unit_price': Decimal('10.00')},
        ]
        
        items = []
        for item_data in items_data:
            item, _ = Item.objects.get_or_create(
                name=item_data['name'],
                group=item_data['group'],
                defaults={
                    'unit': kg_unit if kg_unit else None,
                    'unit_price': item_data['unit_price'],
                    'uom': 'kg' if item_data['group'] != 'Fuel' else 'L',
                }
            )
            items.append(item)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Items: {len(items)} created'))

        # Create Inventory
        storage_locations = [loc for loc in locations if 'Store' in loc.name or loc.type == 'Service']
        storage_location = storage_locations[0] if storage_locations else locations[0]
        
        for item in items[:3]:
            inventory, _ = ItemInventory.objects.get_or_create(
                farm=farm,
                item=item,
                location=storage_location,
                defaults={'qty': Decimal('500.00')}
            )
            
            ItemInventoryBatch.objects.get_or_create(
                inventory=inventory,
                batch_number=f'BATCH-{item.name[:10]}-2026-01',
                defaults={
                    'qty': Decimal('500.00'),
                    'expiry_date': date.today() + timedelta(days=365),
                }
            )
        self._log('Inventory initialized')

        # Phase 4: Agricultural Setup
        self.stdout.write(self.style.HTTP_INFO('\n🌱 Phase 4: Agricultural Setup'))
        
        crops_data = [
            {'name': 'قمح', 'max_yield_per_ha': Decimal('5.0')},
            {'name': 'ذرة', 'max_yield_per_ha': Decimal('8.0')},
            {'name': 'طماطم', 'max_yield_per_ha': Decimal('40.0')},
            {'name': 'بن', 'max_yield_per_ha': Decimal('2.0')},
        ]
        
        crops = []
        for crop_data in crops_data:
            crop = Crop.objects.filter(name=crop_data['name']).first()
            if not crop:
                crop = Crop.objects.create(**crop_data)
            crops.append(crop)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Crops: {len(crops)} created'))

        # Create Varieties
        varieties = []
        for crop in crops:
            var, _ = CropVariety.objects.get_or_create(
                crop=crop,
                name=f'{crop.name} محلي',
                defaults={'is_active': True}
            )
            varieties.append(var)
        self._log(f'Varieties: {len(varieties)} created')

        # Create Tasks
        # Task requires a crop reference, use first available
        default_crop = crops[0] if crops else Crop.objects.first()
        tasks_data = [
            {'name': 'تحضير الأرض', 'stage': 'التحضير'},
            {'name': 'الزراعة', 'stage': 'الزراعة'},
            {'name': 'الري', 'stage': 'الرعاية'},
            {'name': 'التسميد', 'stage': 'الرعاية'},
            {'name': 'الحصاد', 'stage': 'الحصاد'},
        ]
        
        tasks = []
        for task_data in tasks_data:
            task = Task.objects.filter(name=task_data['name']).first()
            if not task and default_crop:
                task = Task.objects.create(
                    crop=default_crop,
                    **task_data
                )
            if task:
                tasks.append(task)
        self._log(f'Tasks: {len(tasks)} created')

        # Phase 5: Planning Cycle
        self.stdout.write(self.style.HTTP_INFO('\n📅 Phase 5: Planning Cycle'))
        
        season, _ = Season.objects.get_or_create(
            name='موسم 2026 الزراعي',
            defaults={
                'start_date': date(2026, 1, 1),
                'end_date': date(2026, 12, 31),
                'is_active': True,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Season: {season.name}'))

        # Create Crop Plans
        field_locations = [loc for loc in locations if loc.type in ['Field', 'Orchard']]
        crop_plans = []
        
        for idx, location in enumerate(field_locations[:2]):
            crop = crops[idx] if idx < len(crops) else crops[0]
            plan, _ = CropPlan.objects.get_or_create(
                farm=farm,
                season=season,
                location=location,
                crop=crop,
                defaults={
                    'name': f'خطة {crop.name} - {location.name}',
                    'area': Decimal('30.00'),
                    'expected_yield': Decimal('150.00'),
                    'status': 'active',
                    'start_date': season.start_date,
                    'end_date': season.end_date,
                }
            )
            crop_plans.append(plan)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Crop Plans: {len(crop_plans)} created'))

        # Create Budget Lines
        for plan in crop_plans:
            budget_items = [
                ('materials', Decimal('5000.00')),
                ('materials', Decimal('8000.00')),
                ('labor', Decimal('15000.00')),
            ]
            for category, amount in budget_items:
                CropPlanBudgetLine.objects.get_or_create(
                    crop_plan=plan,
                    category=category,
                    defaults={'total_budget': amount}
                )
        self._log('Budget lines created')

        # Phase 6: Financial Setup
        self.stdout.write(self.style.HTTP_INFO('\n💰 Phase 6: Financial Setup'))
        
        fiscal_year, _ = FiscalYear.objects.get_or_create(
            farm=farm,
            year=2026,
            defaults={
                'start_date': date(2026, 1, 1),
                'end_date': date(2026, 12, 31),
                'is_closed': False,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Fiscal Year: {fiscal_year.year}'))

        # Create Fiscal Periods
        for month in range(1, 13):
            start = date(2026, month, 1)
            end = date(2026, 12, 31) if month == 12 else date(2026, month + 1, 1) - timedelta(days=1)
            
            FiscalPeriod.objects.get_or_create(
                fiscal_year=fiscal_year,
                month=month,
                defaults={'start_date': start, 'end_date': end, 'is_closed': False}
            )
        self._log('12 fiscal periods created')

        # Phase 7: Tree Inventory
        self.stdout.write(self.style.HTTP_INFO('\n🌳 Phase 7: Tree Inventory'))
        
        # Use savepoint for Phase 7 to allow rollback on schema issues
        sid = transaction.savepoint()
        try:
            productive, _ = TreeProductivityStatus.objects.get_or_create(
                code='PRODUCTIVE',
                defaults={'name_ar': 'منتج', 'name_en': 'Productive'}
            )
            
            # Get coffee variety for tree inventory
            coffee_variety = CropVariety.objects.filter(crop__name='بن').first()
            if coffee_variety and len(field_locations) > 2:
                stock, created = LocationTreeStock.objects.get_or_create(
                    location=field_locations[2],
                    crop_variety=coffee_variety,
                    defaults={
                        'current_tree_count': 500,
                        'productivity_status': productive,
                        'planting_date': date(2020, 3, 15),
                    }
                )
                
                if created:
                    TreeStockEvent.objects.create(
                        location_tree_stock=stock,
                        event_type='planting',
                        tree_count_delta=500,
                        resulting_tree_count=500,
                        notes='إدخال المخزون الأولي',
                    )
                self._log('Tree inventory initialized')
            else:
                self._log('Skipped tree inventory (no coffee variety)')
            transaction.savepoint_commit(sid)
        except Exception as e:
            transaction.savepoint_rollback(sid)
            self.stdout.write(self.style.WARNING(f'  ⚠ Tree inventory skipped (schema issue): {str(e)[:50]}'))

        # Phase 8: Daily Operations
        self.stdout.write(self.style.HTTP_INFO('\n📝 Phase 8: Daily Operations'))
        
        daily_logs = []
        for days_ago in range(14, 0, -1):
            log_date = date.today() - timedelta(days=days_ago)
            if log_date.weekday() >= 5:
                continue
            
            log, _ = DailyLog.objects.get_or_create(
                farm=farm,
                log_date=log_date,
                defaults={
                    'status': 'approved',
                    'notes': f'سجل يومي - {log_date}',
                    'created_by': admin_user,
                    'approved_by': admin_user,
                    'approved_at': timezone.now(),
                }
            )
            daily_logs.append(log)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Daily Logs: {len(daily_logs)} created'))

        # Create Activities
        activities = []
        for log in daily_logs[:5]:
            task = tasks[len(activities) % len(tasks)]
            
            activity, created = Activity.objects.get_or_create(
                log=log,
                task=task,
                defaults={
                    'days_spent': Decimal('1.0'),
                }
            )
            
            if created and employees:
                for emp in employees[:2]:
                    ActivityEmployee.objects.create(
                        activity=activity,
                        employee=emp,
                        surrah_share=Decimal('1.0'),
                    )
            
            activities.append(activity)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Activities: {len(activities)} created'))

        # Phase 9: Harvest & Sales Cycle
        self.stdout.write(self.style.HTTP_INFO('\n🎯 Phase 9: Harvest & Sales Cycle'))
        
        harvest_lots = []
        for plan in crop_plans[:1]:
            lot, _ = HarvestLot.objects.get_or_create(
                farm=farm,
                crop=plan.crop,
                crop_plan=plan,
                harvest_date=date.today() - timedelta(days=5),
                defaults={
                    'quantity': Decimal('500.00'),
                    'grade': 'First',
                    'location': plan.location,
                    'uom': 'kg',
                }
            )
            harvest_lots.append(lot)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Harvest Lots: {len(harvest_lots)} created'))

        # Create Customer
        customer, _ = Customer.objects.get_or_create(
            name='شركة الأمانة التجارية',
            defaults={
                'customer_type': 'wholesaler',
                'phone': '+967-1-234567',
                'address': 'صنعاء - شارع الستين',
            }
        )
        self._log(f'Customer: {customer.name}')

        # Create Sales Invoice
        for lot in harvest_lots:
            invoice, created = SalesInvoice.objects.get_or_create(
                farm=farm,
                customer=customer,
                invoice_date=date.today(),
                defaults={
                    'status': 'approved',
                    'total_amount': lot.quantity * Decimal('100.00'),
                    'created_by': admin_user,
                }
            )
            
            if created and items:
                SalesInvoiceItem.objects.create(
                    invoice=invoice,
                    item=items[0],
                    description=f'حصاد {lot.crop.name}',
                    qty=lot.quantity,
                    unit_price=Decimal('100.00'),
                    total=lot.quantity * Decimal('100.00'),
                )
        self._log('Sales invoices created')

        # Phase 10: Verify
        self.stdout.write(self.style.HTTP_INFO('\n📊 Phase 10: Verifying Financial Entries'))
        ledger_count = FinancialLedger.objects.filter(farm=farm).count()
        if ledger_count > 0:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Ledger Entries: {ledger_count} auto-generated'))
        else:
            self.stdout.write(self.style.WARNING(f'  ⚠ No ledger entries found'))

        # Summary
        self._print_summary(farm)
        self.stdout.write(self.style.SUCCESS('\n✅ Golden Farm created successfully!'))

    def _log(self, message):
        if self.verbose:
            self.stdout.write(f'  → {message}')

    def _clean_golden_farm(self):
        """Remove existing Golden Farm data"""
        from smart_agri.core.models import Farm
        
        self.stdout.write(self.style.WARNING('🗑️ Cleaning existing Golden Farm...'))
        try:
            farm = Farm.objects.filter(name='المزرعة الذهبية - Golden Farm').first()
            if farm:
                farm.delete()
                self.stdout.write(self.style.SUCCESS('  ✓ Cleaned successfully'))
            else:
                self.stdout.write('  → No existing Golden Farm found')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))

    def _print_summary(self, farm):
        """Print summary of created data"""
        from smart_agri.core.models import Location, Employee, Asset, CropPlan, DailyLog, Activity
        from smart_agri.core.models import LocationTreeStock, HarvestLot
        from smart_agri.inventory.models import ItemInventory
        from smart_agri.finance.models import FinancialLedger
        from smart_agri.sales.models import SalesInvoice
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('📊 GOLDEN FARM SUMMARY'))
        self.stdout.write('=' * 70)
        
        # Use try-except to handle potential schema issues
        try:
            summary_data = [
                ('Locations', Location.objects.filter(farm=farm).count()),
                ('Employees', Employee.objects.filter(farm=farm).count()),
                ('Assets', Asset.objects.filter(farm=farm).count()),
                ('Crop Plans', CropPlan.objects.filter(farm=farm).count()),
                ('Daily Logs', DailyLog.objects.filter(farm=farm).count()),
                ('Activities', Activity.objects.filter(log__farm=farm).count()),
                ('Harvest Lots', HarvestLot.objects.filter(farm=farm).count()),
                ('Inventory Items', ItemInventory.objects.filter(farm=farm).count()),
                ('Ledger Entries', FinancialLedger.objects.filter(farm=farm).count()),
                ('Sales Invoices', SalesInvoice.objects.filter(farm=farm).count()),
            ]
            
            for label, count in summary_data:
                self.stdout.write(f'  {label}: {count}')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Summary error: {str(e)[:50]}'))
        
        self.stdout.write('=' * 70)
