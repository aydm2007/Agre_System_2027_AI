import logging
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '[AGRI-GUARDIAN] Inject Ultimate Edition Features (CostCenters, Recipes, Dynamic Approvals) into Golden Farm'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n' + '=' * 70))
        self.stdout.write(self.style.WARNING('🌾 AGRI-GUARDIAN: Ultimate Features Seeder For Golden Farm'))
        self.stdout.write(self.style.WARNING('=' * 70 + '\n'))

        from smart_agri.core.models import Farm, Crop, CropPlan, DailyLog, Activity, ActivityItem
        from smart_agri.core.models.crop import CropRecipe, CropRecipeMaterial, CropMaterial
        from smart_agri.finance.models import CostCenter, ApprovalRule
        from smart_agri.inventory.models import Item
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin_user = User.objects.filter(username='golden_admin').first()
        farm = Farm.objects.filter(slug='golden-farm').first()

        if not farm:
            self.stdout.write(self.style.ERROR('❌ Golden Farm not found. Please run seed_golden_farm first.'))
            return
            
        # 1. Cost Centers & Analytical Tags
        self.stdout.write(self.style.HTTP_INFO('\n💡 Phase 1: Analytical Segregation'))
        cc, _ = CostCenter.objects.get_or_create(
            farm=farm,
            code="CC-TOMATO-01",
            defaults={"name": "عمليات محصول الطماطم بمزارع العينة", "description": "مركز تكلفة لعمليات الطماطم", "is_active": True}
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Cost Center: {cc.name}'))



        # 2. Crop Recipe (Agronomic BOM)
        self.stdout.write(self.style.HTTP_INFO('\n💡 Phase 2: Agronomic Intelligence (BOM)'))
        crop = Crop.objects.filter(name='طماطم').first()
        item = Item.objects.filter(name__contains='يوريا').first() or Item.objects.filter(group='Fertilizers').first()
        
        if not crop:
            crop, _ = Crop.objects.get_or_create(name='طماطم', defaults={'max_yield_per_ha': Decimal('40.0')})
            
        if not item:
            item, _ = Item.objects.get_or_create(name='سماد يوريا 46%', group='Fertilizers', defaults={'unit_price': Decimal('25.00')})

        recipe, _ = CropRecipe.objects.get_or_create(
            crop=crop,
            name="وصفة الطماطم القياسية - العروة الصيفية",
            defaults={"is_active": True}
        )
        
        crop_mat, _ = CropMaterial.objects.get_or_create(
            crop=crop,
            item=item,
            defaults={"recommended_qty": Decimal("50.00"), "notes": "السماد الأساسي"}
        )
        
        recipe_mat, _ = CropRecipeMaterial.objects.get_or_create(
            recipe=recipe,
            item=item,
            defaults={"standard_qty_per_ha": Decimal("50.00"), "is_active": True}
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Recipe & BOM Material ({item.name}) assigned to {crop.name}'))

        plan = CropPlan.objects.filter(farm=farm, crop=crop).first()
        if plan:
            plan.recipe = recipe
            plan.save()
            self.stdout.write(self.style.SUCCESS(f'  ✓ Enforced standard Recipe on CropPlan: {plan.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'  ⚠ No CropPlan found for {crop.name} to link recipe.'))

        # 3. Dynamic Approval Workflows
        self.stdout.write(self.style.HTTP_INFO('\n💡 Phase 3: Dynamic Approval Workflows'))
        rule, _ = ApprovalRule.objects.get_or_create(
            farm=farm,
            module='EXPENSE',
            action='create',
            cost_center=cc,
            defaults={
                'min_amount': Decimal('1000'),
                'max_amount': Decimal('50000'),
                'required_role': ApprovalRule.ROLE_FINANCE_DIRECTOR,
                'is_active': True
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  ✓ Dynamic Rule created scoped to Cost Center {cc.code}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Ultimate Features Data Injection Complete!'))
        self.stdout.write(self.style.WARNING('You can now test the Variance Engine and Approval dynamically.'))
