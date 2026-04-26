"""
[AGRI-GUARDIAN] BOM Deviation Checker
=====================================
Validates actual material usage against BOM (Bill of Materials) recommendations.
Flags deviations > 20% as per Agri-Guardian Protocol III.

Run as: python manage.py check_bom_deviation [--farm FARM_CODE] [--period PERIOD]
"""

from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from smart_agri.core.models import (
    Farm, CropPlan, CropMaterial, Activity
)
from smart_agri.core.models.activity import ActivityMaterialApplication


class Command(BaseCommand):
    help = '[AGRI-GUARDIAN] Check BOM deviation (20% threshold per Protocol III)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--farm',
            type=str,
            help='Specific farm code to check',
        )
        parser.add_argument(
            '--period',
            type=int,
            default=30,
            help='Period in days to analyze (default: 30)',
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=20.0,
            help='Deviation threshold percentage (default: 20.0)',
        )

    def handle(self, *args, **options):
        farm_code = options.get('farm')
        period_days = options.get('period', 30)
        threshold = Decimal(str(options.get('threshold', 20.0)))
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.WARNING('🧪 AGRI-GUARDIAN: BOM Deviation Checker'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Period: Last {period_days} days')
        self.stdout.write(f'Threshold: {threshold}%')
        self.stdout.write('=' * 70 + '\n')
        
        # Get farms to analyze
        farms = Farm.objects.all()
        if farm_code:
            farms = farms.filter(code=farm_code)
        
        if not farms.exists():
            self.stdout.write(self.style.ERROR('No farms found'))
            return
        
        total_deviations = 0
        total_checks = 0
        
        start_date = date.today() - timedelta(days=period_days)
        
        for farm in farms:
            self.stdout.write(f'\n📋 Farm: {farm.name}')
            self.stdout.write('-' * 50)
            
            # Get active crop plans
            crop_plans = CropPlan.objects.filter(
                farm=farm,
                deleted_at__isnull=True
            ).select_related('crop')
            
            if not crop_plans.exists():
                self.stdout.write('  ⚠️ No active crop plans')
                continue
            
            for plan in crop_plans:
                # Get BOM for this crop
                bom_items = CropMaterial.objects.filter(
                    crop=plan.crop,
                    deleted_at__isnull=True,
                    recommended_qty__isnull=False
                ).select_related('item')
                
                if not bom_items.exists():
                    continue
                
                self.stdout.write(f'\n  🌱 Crop Plan: {plan.crop.name}')
                
                for bom in bom_items:
                    # Calculate recommended usage based on area
                    area = getattr(plan, 'area', None) or Decimal('1')
                    recommended_total = bom.recommended_qty * area
                    
                    # Get actual usage from activities
                    actual_usage = ActivityMaterialApplication.objects.filter(
                        activity__log__farm=farm,
                        item=bom.item,
                        activity__log__log_date__gte=start_date,
                        deleted_at__isnull=True
                    ).aggregate(total=Sum('quantity'))['total'] or Decimal('0')
                    
                    if recommended_total == 0:
                        continue
                    
                    total_checks += 1
                    
                    # Calculate deviation
                    deviation = ((actual_usage - recommended_total) / recommended_total) * 100
                    
                    status = '✅'
                    style = self.style.SUCCESS
                    
                    if abs(deviation) > threshold:
                        status = '⚠️' if deviation > 0 else '📉'
                        style = self.style.WARNING if deviation > 0 else self.style.ERROR
                        total_deviations += 1
                    
                    self.stdout.write(style(
                        f'    {status} {bom.item.name}: '
                        f'BOM={recommended_total:.2f}, Actual={actual_usage:.2f}, '
                        f'Deviation={deviation:+.1f}%'
                    ))
        
        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.HTTP_INFO('📊 BOM DEVIATION SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'  Total items checked: {total_checks}')
        self.stdout.write(f'  Deviations > {threshold}%: {total_deviations}')
        
        if total_deviations > 0:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️ {total_deviations} item(s) exceed the {threshold}% deviation threshold'
            ))
            self.stdout.write(self.style.WARNING(
                '   Per Agri-Guardian Protocol III, these require Supervisor Approval'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ All material usage within BOM tolerance'))
