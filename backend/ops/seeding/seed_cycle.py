import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()
from smart_agri.core.models import Crop, Farm, FarmCrop, FarmSettings, Season

farm = Farm.objects.get(id=28)
print(f'Farm: {farm.name} (id={farm.id})')

# Create Season
season, s_created = Season.objects.get_or_create(
    name='موسم 2026',
    defaults={'start_date':'2026-01-01', 'end_date':'2026-12-31'}
)
print(f'Season: {season.name} (id={season.id}) [{"NEW" if s_created else "EXISTS"}]')

# Create Crops
crops_data = [
    {'name':'المانجو', 'is_perennial':True, 'mode':'strict'},
    {'name':'الموز', 'is_perennial':True, 'mode':'strict'},
    {'name':'القمح', 'is_perennial':False, 'mode':'simple'},
]
for cd in crops_data:
    crop, created = Crop.objects.get_or_create(
        name=cd['name'],
        defaults={'is_perennial':cd['is_perennial'], 'mode':cd['mode']}
    )
    print(f'Crop: {crop.name} (id={crop.id}, perennial={crop.is_perennial}) [{"NEW" if created else "EXISTS"}]')
    fc, fc_created = FarmCrop.objects.get_or_create(farm=farm, crop=crop)
    print(f'  FarmCrop: farm={farm.name} -> {crop.name} (id={fc.id}) [{"NEW" if fc_created else "EXISTS"}]')

# Ensure FarmSettings exist
fs, fs_created = FarmSettings.objects.get_or_create(farm=farm, defaults={'mode':'simple'})
print(f'FarmSettings: mode={fs.mode} [{"NEW" if fs_created else "EXISTS"}]')

print('\n=== SEED COMPLETE ===')
