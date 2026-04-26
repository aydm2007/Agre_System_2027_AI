import pytest
from datetime import date
from smart_agri.core.models import Crop, CropVariety, DailyLog, Activity, Farm

@pytest.mark.django_db
def test_perennial_crop_creation():
    farm, _ = Farm.objects.get_or_create(name="Test Farm", code="T01", area=10)
    
    mango, _ = Crop.objects.get_or_create(name="مانجو", farm=farm, mode="Open", is_perennial=True)
    awees, _ = CropVariety.objects.get_or_create(crop=mango, name="عويس")
    
    banana, _ = Crop.objects.get_or_create(name="موز", farm=farm, mode="Open", is_perennial=True)
    cav, _ = CropVariety.objects.get_or_create(crop=banana, name="كافنديش")
    
    # Assert crops exist
    mango_db = Crop.objects.get(name="مانجو")
    assert mango_db.is_perennial == True
    assert mango_db.varieties.count() == 1
    assert mango_db.varieties.first().name == "عويس"
    
    log = DailyLog.objects.create(farm=farm, crop=mango, log_date=date.today(), notes="API Test")
    act = Activity.objects.create(log=log, activity_type="Service", variety=awees, trees_count=100, activity_name="Harvest Test")
    
    assert act.variety.name == "عويس"
    assert act.trees_count == 100
    
    print("Pytest: Successfully verified robust perennial crop management via Django Models")
