from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Crop, CropProduct, CropRecipe, CropRecipeMaterial, DailyLog, Farm, FarmCrop, Task
from smart_agri.core.models.activity import Activity, ActivityEmployee, ActivityItem
from smart_agri.core.models.farm import Location
from smart_agri.core.models.planning import CropPlan, CropPlanBudgetLine, CropPlanLocation, PlannedActivity
from smart_agri.core.models.report import VarianceAlert
from smart_agri.core.models.settings import FarmSettings
from smart_agri.inventory.models import Item, ItemInventory
from smart_agri.finance.models import FinancialLedger, FiscalPeriod, FiscalYear


class ServiceCardAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('service_manager', password='pass', is_staff=True)
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        self.user.groups.add(manager_group)

        self.farm = Farm.objects.create(name='Farm Alpha', slug='farm-alpha', region='A')
        FarmMembership.objects.create(user=self.user, farm=self.farm, role='Manager')

        self.crop = Crop.objects.create(name='Tomato', mode='Open')
        FarmCrop.objects.create(farm=self.farm, crop=self.crop)
        self.other_crop = Crop.objects.create(name='Olive', mode='Open')
        self.location = Location.objects.create(name='Zone 1', farm=self.farm)

        Task.objects.create(crop=self.crop, stage='Preparation', name='Soil tillage', requires_machinery=True, is_asset_task=True, asset_type='tractor')
        Task.objects.create(crop=self.crop, stage='Irrigation', name='Drip cycle', requires_well=True)
        Task.objects.create(crop=self.crop, stage='Fertilization', name='Foliar spray', requires_area=True)
        Task.objects.create(crop=self.crop, stage='Harvest', name='Picking', is_harvest_task=True)
        Task.objects.create(crop=self.crop, stage='Preparation', name='Manual pruning', requires_tree_count=True)
        self.primary_task = Task.objects.create(crop=self.crop, stage='Control', name='Inspection')
        self.material_task = Task.objects.create(
            crop=self.crop,
            stage='Fertilization',
            name='Targeted feeding',
            archetype=Task.Archetype.MATERIAL_INTENSIVE,
        )
        self.plan = CropPlan.objects.create(
            farm=self.farm,
            crop=self.crop,
            name='Tomato Master Plan',
            start_date=date.today().replace(day=1),
            end_date=date.today().replace(month=12, day=31),
            budget_total=Decimal('500.0000'),
            area=Decimal('2.000'),
            status='active',
        )
        self.item = Item.objects.create(
            name='NPK',
            group='Fertilizer',
            uom='kg',
            unit_price=Decimal('10.000'),
        )
        self.recipe = CropRecipe.objects.create(crop=self.crop, name='Tomato Feeding')
        CropRecipeMaterial.objects.create(
            recipe=self.recipe,
            item=self.item,
            standard_qty_per_ha=Decimal('5.000'),
        )
        ItemInventory.objects.create(
            farm=self.farm,
            item=self.item,
            qty=Decimal('50.000'),
            uom='kg',
        )
        self.plan.recipe = self.recipe
        self.plan.save(update_fields=['recipe'])
        FarmSettings.objects.create(
            farm=self.farm,
            mode=FarmSettings.MODE_SIMPLE,
            cost_visibility=FarmSettings.COST_VISIBILITY_SUMMARIZED,
            variance_behavior=FarmSettings.VARIANCE_BEHAVIOR_WARN,
            approval_profile=FarmSettings.APPROVAL_PROFILE_TIERED,
            contract_mode=FarmSettings.CONTRACT_MODE_OPERATIONAL_ONLY,
            treasury_visibility=FarmSettings.TREASURY_VISIBILITY_HIDDEN,
            fixed_asset_mode=FarmSettings.FIXED_ASSET_MODE_TRACKING_ONLY,
        )
        CropPlanLocation.objects.create(crop_plan=self.plan, location=self.location)
        PlannedActivity.objects.create(
            crop_plan=self.plan,
            task=self.primary_task,
            planned_date=date.today(),
            estimated_hours=Decimal('4.00'),
        )
        CropPlanBudgetLine.objects.create(
            crop_plan=self.plan,
            task=self.primary_task,
            category=CropPlanBudgetLine.CATEGORY_LABOR,
            total_budget=Decimal('100.0000'),
        )
        PlannedActivity.objects.create(
            crop_plan=self.plan,
            task=self.material_task,
            planned_date=date.today(),
            estimated_hours=Decimal('2.00'),
        )

        Task.objects.create(crop=self.other_crop, stage='Maintenance', name='Unused service', requires_machinery=True)

        fiscal_year = FiscalYear.objects.create(
            farm=self.farm,
            year=date.today().year,
            start_date=date(date.today().year, 1, 1),
            end_date=date(date.today().year, 12, 31),
        )
        FiscalPeriod.objects.create(
            fiscal_year=fiscal_year,
            month=date.today().month,
            start_date=date(date.today().year, date.today().month, 1),
            end_date=date(date.today().year, date.today().month, 28),
            status=FiscalPeriod.STATUS_OPEN,
        )

        self.log = DailyLog.objects.create(
            farm=self.farm,
            log_date=date.today(),
            status='APPROVED',
            variance_status='CRITICAL',
            created_by=self.user,
            updated_by=self.user,
        )
        self.activity = Activity.objects.create(
            log=self.log,
            crop=self.crop,
            crop_plan=self.plan,
            task=self.primary_task,
            cost_total=Decimal('123.4500'),
        )
        self.material_activity = Activity.objects.create(
            log=self.log,
            crop=self.crop,
            crop_plan=self.plan,
            task=self.material_task,
            cost_total=Decimal('75.0000'),
            task_contract_snapshot={
                **self.material_task.get_effective_contract(),
                'smart_cards': {
                    **self.material_task.get_effective_contract().get('smart_cards', {}),
                    'labor': {'enabled': True},
                },
                'presentation': {
                    **self.material_task.get_effective_contract().get('presentation', {}),
                    'simple_preview': ['execution', 'materials', 'labor', 'control', 'variance'],
                },
            },
        )
        ActivityItem.objects.create(
            activity=self.material_activity,
            item=self.item,
            qty=Decimal('6.000'),
            uom='kg',
            cost_per_unit=Decimal('12.0000'),
            total_cost=Decimal('72.0000'),
        )
        ActivityEmployee.objects.create(
            activity=self.material_activity,
            labor_type=ActivityEmployee.LABOR_CASUAL_BATCH,
            labor_batch_label='Village team',
            workers_count=Decimal('4.00'),
            surrah_share=Decimal('2.00'),
        )
        VarianceAlert.objects.create(
            farm=self.farm,
            daily_log=self.log,
            activity_name='Inspection',
            planned_cost=Decimal('100.0000'),
            actual_cost=Decimal('123.4500'),
            variance_amount=Decimal('23.4500'),
            variance_percentage=Decimal('23.45'),
            alert_message='Budget overrun',
            status=VarianceAlert.ALERT_STATUS_UNINVESTIGATED,
        )
        FinancialLedger.objects.create(
            farm=self.farm,
            activity=self.activity,
            account_code=FinancialLedger.ACCOUNT_WIP,
            debit=Decimal('123.4500'),
            credit=Decimal('0.0000'),
            description='Service card ledger snapshot',
            created_by=self.user,
        )

        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse('service-cards-list')

    def test_service_cards_returns_grouped_metrics(self):
        response = self.client.get(self.url, {'farm_id': self.farm.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        card = response.data[0]
        self.assertEqual(card['crop']['name'], 'Tomato')
        metrics = card['metrics']
        self.assertEqual(metrics['total'], 7)
        self.assertEqual(metrics['machinery'], 1)
        self.assertEqual(metrics['well'], 1)
        self.assertEqual(metrics['area'], 1)
        self.assertEqual(metrics['tree_count'], 1)
        self.assertIn('tractor', metrics['asset_types'])
        self.assertEqual(metrics['asset_tasks_missing_type'], 0)

        stages = card['stage_groups']
        stage_names = {entry['stage'] for entry in stages}
        self.assertIn('Preparation', stage_names)
        self.assertIn('Irrigation', stage_names)
        self.assertIn('Harvest', stage_names)

        stack = card['smart_card_stack']
        self.assertEqual(len(stack), 3)
        control_card = next(c for c in stack if c['card_key'] == 'control')
        self.assertEqual(control_card['metrics']['total_logs'], 1)
        self.assertEqual(control_card['metrics']['critical_logs'], 1)

        variance_card = next(c for c in stack if c['card_key'] == 'variance')
        self.assertEqual(variance_card['metrics']['total_alerts'], 1)
        self.assertEqual(variance_card['metrics']['open_alerts'], 1)
        self.assertEqual(variance_card['metrics']['total_variance'], '23.4500')

        financial_card = next(c for c in stack if c['card_key'] == 'financial_trace')
        self.assertEqual(financial_card['metrics']['entries_count'], 1)
        self.assertEqual(financial_card['metrics']['debit_total'], '123.4500')
        self.assertEqual(financial_card['metrics']['credit_total'], '0.0000')
        self.assertEqual(card['visibility_level'], 'operations_only')
        self.assertEqual(card['cost_display_mode'], FarmSettings.COST_VISIBILITY_SUMMARIZED)
        self.assertEqual(card['policy_snapshot']['mode'], FarmSettings.MODE_SIMPLE)
        self.assertEqual(
            card['policy_snapshot']['approval_profile'],
            FarmSettings.APPROVAL_PROFILE_TIERED,
        )

    def test_service_cards_include_plan_and_task_focus_for_daily_log_context(self):
        response = self.client.get(
            self.url,
            {
                'farm_id': self.farm.id,
                'crop_id': self.crop.id,
                'task_id': self.primary_task.id,
                'crop_plan_id': self.plan.id,
                'location_ids': str(self.location.id),
                'date': date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        card = response.data[0]

        stack = card['smart_card_stack']
        self.assertEqual([entry['card_key'] for entry in stack], ['execution', 'control', 'variance'])
        execution_card = stack[0]
        self.assertEqual(execution_card['mode_visibility'], 'simple_preview')
        self.assertEqual(execution_card['metrics']['task_name'], 'Inspection')
        self.assertEqual(execution_card['metrics']['plan_name'], 'Tomato Master Plan')
        self.assertEqual(execution_card['metrics']['plan_status'], 'active')
        self.assertEqual(execution_card['metrics']['budget_total'], '500.0000')
        self.assertEqual(execution_card['metrics']['daily_total_activities'], 1)
        self.assertEqual(execution_card['metrics']['daily_total_cost'], '123.4500')
        self.assertEqual(execution_card['metrics']['planned_count'], 1)
        self.assertEqual(execution_card['metrics']['executed_count'], 1)
        self.assertEqual(execution_card['metrics']['planned_tasks'], 2)
        self.assertEqual(execution_card['metrics']['completed_tasks'], 2)
        self.assertEqual(execution_card['metrics']['plan_progress_pct'], 100.0)
        self.assertEqual(execution_card['metrics']['actual_total'], '198.4500')
        self.assertEqual(execution_card['metrics']['variance_total'], '-301.5500')
        self.assertEqual(execution_card['metrics']['variance_pct'], Decimal('-60.31'))
        self.assertEqual(execution_card['metrics']['planned_locations'], 1)
        self.assertEqual(execution_card['metrics']['matched_locations'], 1)
        self.assertEqual(execution_card['metrics']['schedule_status'], 'due_today')
        self.assertEqual(execution_card['metrics']['cost_display_mode'], FarmSettings.COST_VISIBILITY_SUMMARIZED)
        self.assertEqual(execution_card['metrics']['visibility_level'], 'operations_only')
        self.assertEqual(execution_card['metrics']['location_coverage_pct'], 100.0)
        self.assertEqual(execution_card['metrics']['open_variances'], 1)
        self.assertEqual(execution_card['flags'], [])

    def test_service_cards_harvest_task_uses_product_pack_uom_without_500(self):
        harvest_task = Task.objects.create(
            crop=self.crop,
            stage='Harvest',
            name='Harvest proof',
            is_harvest_task=True,
        )
        CropProduct.objects.create(crop=self.crop, name='Tomato Box', pack_uom='kg')

        response = self.client.get(
            self.url,
            {
                'farm_id': self.farm.id,
                'crop_id': self.crop.id,
                'task_id': harvest_task.id,
                'crop_plan_id': self.plan.id,
                'location_ids': str(self.location.id),
                'date': date.today().isoformat(),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stack = response.data[0]['smart_card_stack']
        harvest_card = next(card for card in stack if card['card_key'] == 'harvest')
        self.assertEqual(harvest_card['metrics']['available_products'][0]['uom'], 'kg')

    def test_service_cards_emit_no_plan_schedule_status_when_active_plan_missing(self):
        self.plan.status = 'draft'
        self.plan.save(update_fields=['status'])
        response = self.client.get(
            self.url,
            {
                'farm_id': self.farm.id,
                'crop_id': self.crop.id,
                'task_id': self.primary_task.id,
                'date': date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        execution_card = response.data[0]['smart_card_stack'][0]
        self.assertEqual(execution_card['metrics']['schedule_status'], 'no_plan')
        self.assertIn('missing_active_plan', execution_card['flags'])

    def test_service_cards_emit_material_stack_from_activity_snapshot(self):
        response = self.client.get(
            self.url,
            {
                'farm_id': self.farm.id,
                'crop_id': self.crop.id,
                'task_id': self.material_task.id,
                'crop_plan_id': self.plan.id,
                'date': date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        card = response.data[0]
        stack = card['smart_card_stack']
        self.assertEqual(
            [entry['card_key'] for entry in stack],
            ['execution', 'materials', 'labor', 'control', 'variance'],
        )
        materials_card = next(entry for entry in stack if entry['card_key'] == 'materials')
        self.assertEqual(materials_card['data_source'], 'activity_items')
        self.assertEqual(materials_card['metrics']['planned_qty'], '10.0000')
        self.assertEqual(materials_card['metrics']['actual_qty'], '6.0000')
        self.assertEqual(materials_card['metrics']['qty_variance'], '-4.0000')
        self.assertEqual(materials_card['metrics']['planned_cost'], '100.0000')
        self.assertEqual(materials_card['metrics']['actual_cost'], '72.0000')
        self.assertEqual(materials_card['metrics']['cost_variance'], '-28.0000')
        self.assertNotIn('line_items', materials_card['metrics'])
        self.assertEqual(materials_card['policy']['cost_visibility'], FarmSettings.COST_VISIBILITY_SUMMARIZED)
        self.assertFalse(materials_card['policy']['full_cost_allowed'])
        self.assertIn('crop_plan.recipe', materials_card['source_refs'])
        self.assertIn('financial_ledger', materials_card['source_refs'])

        labor_card = next(entry for entry in stack if entry['card_key'] == 'labor')
        self.assertEqual(labor_card['metrics']['workers_count'], '4.0000')
        self.assertEqual(labor_card['metrics']['surrah_share'], '2.0000')
        self.assertTrue(labor_card['policy']['backend_costing_only'])

    def test_service_cards_fallback_to_task_contract_when_snapshot_missing(self):
        self.material_activity.task_contract_snapshot = {}
        self.material_activity.save(update_fields=['task_contract_snapshot'])
        response = self.client.get(
            self.url,
            {
                'farm_id': self.farm.id,
                'crop_id': self.crop.id,
                'task_id': self.material_task.id,
                'crop_plan_id': self.plan.id,
                'date': date.today().isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stack = response.data[0]['smart_card_stack']
        card_keys = [entry['card_key'] for entry in stack]
        self.assertIn('materials', card_keys)
        self.assertIn('control', card_keys)

    def test_service_cards_requires_farm_access(self):
        outsider = User.objects.create_user('outsider', password='pass')
        client = APIClient()
        client.force_authenticate(outsider)
        response = client.get(self.url, {'farm_id': self.farm.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
