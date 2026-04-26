import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()
from smart_agri.core.models import Crop, Task

crops = {c.name: c for c in Crop.objects.filter(name__in=['المانجو', 'الموز', 'القمح'])}

# Tasks structure: {crop_name: [{name, stage, archetype, flags}]}
tasks_map = {
    'المانجو': [
        {'name': 'ري المانجو', 'stage': 'رعاية', 'archetype': 'IRRIGATION', 'requires_well': True},
        {'name': 'تسميد المانجو', 'stage': 'رعاية', 'archetype': 'MATERIAL_INTENSIVE'},
        {'name': 'رش مبيدات المانجو', 'stage': 'حماية', 'archetype': 'MATERIAL_INTENSIVE'},
        {'name': 'تقليم المانجو', 'stage': 'رعاية', 'archetype': 'PERENNIAL_SERVICE', 'requires_tree_count': True, 'is_perennial_procedure': True},
        {'name': 'حصاد المانجو', 'stage': 'حصاد', 'archetype': 'HARVEST', 'is_harvest_task': True},
        {'name': 'حراثة المانجو', 'stage': 'تحضير', 'archetype': 'MACHINERY', 'requires_machinery': True, 'requires_area': True},
    ],
    'الموز': [
        {'name': 'ري الموز', 'stage': 'رعاية', 'archetype': 'IRRIGATION', 'requires_well': True},
        {'name': 'تسميد الموز', 'stage': 'رعاية', 'archetype': 'MATERIAL_INTENSIVE'},
        {'name': 'رش مبيدات الموز', 'stage': 'حماية', 'archetype': 'MATERIAL_INTENSIVE'},
        {'name': 'تنظيف فسائل الموز', 'stage': 'رعاية', 'archetype': 'PERENNIAL_SERVICE', 'requires_tree_count': True, 'is_perennial_procedure': True},
        {'name': 'حصاد الموز', 'stage': 'حصاد', 'archetype': 'HARVEST', 'is_harvest_task': True},
    ],
    'القمح': [
        {'name': 'ري القمح', 'stage': 'نمو', 'archetype': 'IRRIGATION', 'requires_well': True},
        {'name': 'تسميد القمح', 'stage': 'نمو', 'archetype': 'MATERIAL_INTENSIVE'},
        {'name': 'رش مبيدات القمح', 'stage': 'حماية', 'archetype': 'MATERIAL_INTENSIVE'},
        {'name': 'حراثة القمح', 'stage': 'تحضير', 'archetype': 'MACHINERY', 'requires_machinery': True, 'requires_area': True},
        {'name': 'حصاد القمح', 'stage': 'حصاد', 'archetype': 'HARVEST', 'is_harvest_task': True},
    ],
}

for crop_name, tasks in tasks_map.items():
    crop = crops[crop_name]
    for td in tasks:
        t, created = Task.objects.get_or_create(
            crop=crop,
            name=td['name'],
            defaults={
                'stage': td['stage'],
                'archetype': td.get('archetype', 'GENERAL'),
                'requires_well': td.get('requires_well', False),
                'requires_machinery': td.get('requires_machinery', False),
                'requires_area': td.get('requires_area', False),
                'is_harvest_task': td.get('is_harvest_task', False),
                'requires_tree_count': td.get('requires_tree_count', False),
                'is_perennial_procedure': td.get('is_perennial_procedure', False),
            }
        )
        print(f'  Task: {t.name} (id={t.id}, arch={t.archetype}) [{"NEW" if created else "EXISTS"}]')
    print()

print('=== TASKS SEEDED ===')
