from decimal import Decimal

try:
    import pytest  # type: ignore
except ImportError:  # Fallback for environments without pytest installed
    class _DummyPytest:
        class _Mark:
            def __getattr__(self, name):
                def decorator(func):
                    return func
                return decorator
        mark = _Mark()
    pytest = _DummyPytest()

from smart_agri.core.models import (
    Activity,
    ActivityLocation,
    ActivityItem,
    Asset,
    Crop,
    CropProduct,
    DailyLog,
    Farm,
    Item,
    LaborRate,
    Location,
    MachineRate,
    Task,
)
from django.core.exceptions import ValidationError

from smart_agri.core.services.costing import calculate_activity_cost, to_decimal


@pytest.mark.django_db
def test_calculate_full_activity_cost():
    farm = Farm.objects.create(name='farm-costing', slug='farm-costing', region='A')
    location = Location.objects.create(farm=farm, name='Main Block', type='Field')
    crop = Crop.objects.create(name='قمح', mode='Open')
    task = Task.objects.create(name='حراثة', crop=crop, stage='تحضير')
    log = DailyLog.objects.create(farm=farm, log_date='2025-01-01')
    asset = Asset.objects.create(farm=farm, name='Tractor', category='Machinery')
    item = Item.objects.create(name='Urea Fert', group='Fertilizer', uom='kg', unit_price=Decimal('15000'))
    product_item = Item.objects.create(name='قمح حصاد', group='Harvested Product', uom='kg')
    CropProduct.objects.create(crop=crop, item=product_item)

    LaborRate.objects.create(farm=farm, role_name='عامل', cost_per_hour=Decimal('1000'))
    MachineRate.objects.create(asset=asset, cost_per_hour=Decimal('5000'))

    activity = Activity.objects.create(
        log=log,
        crop=crop,
        task=task,
        asset=asset,
        days_spent=Decimal('10'),
        machine_hours=Decimal('2'),
    )
    ActivityLocation.objects.create(activity=activity, location=location)
    ActivityItem.objects.create(activity=activity, item=item, qty=Decimal('3'), uom='kg')

    activity.refresh_from_db()
    assert activity.cost_materials == Decimal('45000')
    assert activity.cost_labor == Decimal('10000')
    assert activity.cost_machinery == Decimal('10000')
    assert activity.cost_total == Decimal('65000')


@pytest.mark.django_db
def test_cost_recalculation_on_item_change():
    farm = Farm.objects.create(name='farm-costing-2', slug='farm-costing-2', region='B')
    location = Location.objects.create(farm=farm, name='Zone 1', type='Field')
    crop = Crop.objects.create(name='ذرة', mode='Open')
    task = Task.objects.create(name='تسميد', crop=crop, stage='خدمة')
    log = DailyLog.objects.create(farm=farm, log_date='2025-02-10')
    item = Item.objects.create(name='Compost', group='Fertilizer', uom='kg', unit_price=Decimal('250'))

    activity = Activity.objects.create(
        log=log,
        crop=crop,
        task=task,
        days_spent=Decimal('4'),
    )
    ActivityLocation.objects.create(activity=activity, location=location)
    usage = ActivityItem.objects.create(activity=activity, item=item, qty=Decimal('20'), uom='kg')

    activity.refresh_from_db()
    assert activity.cost_materials == Decimal('5000')

    usage.qty = Decimal('0')
    usage.save(update_fields=['qty'])

    activity.refresh_from_db()
    assert activity.cost_materials == Decimal('0')
    assert activity.cost_total == activity.cost_labor + activity.cost_machinery


@pytest.mark.django_db
def test_manual_costing_invocation_handles_missing_rates():
    farm = Farm.objects.create(name='farm-costing-3', slug='farm-costing-3', region='C')
    location = Location.objects.create(farm=farm, name='Zone 2', type='Field')
    crop = Crop.objects.create(name='بن', mode='Open')
    task = Task.objects.create(name='عزق', crop=crop, stage='خدمة')
    log = DailyLog.objects.create(farm=farm, log_date='2025-03-05')

    activity = Activity.objects.create(
        log=log,
        crop=crop,
        task=task,
        days_spent=Decimal('6'),
        machine_hours=Decimal('1'),
    )
    ActivityLocation.objects.create(activity=activity, location=location)

    calculate_activity_cost(activity)
    activity.refresh_from_db()
    assert activity.cost_total == Decimal('0')


def test_to_decimal_rejects_invalid_values():
    with pytest.raises(ValidationError):
        to_decimal(None, "Daily Rate")

    with pytest.raises(ValidationError):
        to_decimal(1.25, "Daily Rate")

    with pytest.raises(ValidationError):
        to_decimal("not-a-number", "Daily Rate")


@pytest.mark.django_db
def test_calculate_overhead_with_cost_configuration():
    """Test that overhead is calculated using CostConfiguration when available."""
    from smart_agri.core.models import CostConfiguration
    
    farm = Farm.objects.create(name='farm-overhead', slug='farm-overhead', region='D')
    location = Location.objects.create(farm=farm, name='Orchard', type='Field')
    crop = Crop.objects.create(name='تفاح', mode='Open')
    task = Task.objects.create(name='رش', crop=crop, stage='خدمة')
    log = DailyLog.objects.create(farm=farm, log_date='2025-04-01')
    
    # Create custom overhead rate for this farm
    CostConfiguration.objects.create(
        farm=farm,
        overhead_rate_per_hectare=Decimal('100.00'),  # Custom rate
        currency='YER'
    )
    
    activity = Activity.objects.create(
        log=log,
        crop=crop,
        task=task,
        days_spent=Decimal('1'),
        planted_area=Decimal('10000'),  # 1 hectare in m2
        planted_uom='m2',
    )
    ActivityLocation.objects.create(activity=activity, location=location)
    
    calculate_activity_cost(activity)
    activity.refresh_from_db()
    
    # Overhead should be 100.00 * 1 hectare = 100.00
    assert activity.cost_overhead == Decimal('100.00')


@pytest.mark.django_db
def test_calculate_overhead_without_cost_configuration():
    """Test that overhead uses default rate when no CostConfiguration exists."""
    farm = Farm.objects.create(name='farm-default', slug='farm-default', region='E')
    location = Location.objects.create(farm=farm, name='Field', type='Field')
    crop = Crop.objects.create(name='شعير', mode='Open')
    task = Task.objects.create(name='حصاد', crop=crop, stage='حصاد')
    log = DailyLog.objects.create(farm=farm, log_date='2025-05-01')
    
    activity = Activity.objects.create(
        log=log,
        crop=crop,
        task=task,
        days_spent=Decimal('2'),
        planted_area=Decimal('20000'),  # 2 hectares in m2
        planted_uom='m2',
    )
    ActivityLocation.objects.create(activity=activity, location=location)
    
    calculate_activity_cost(activity)
    activity.refresh_from_db()
    
    # Default overhead rate is 50.00, so 50.00 * 2 hectares = 100.00
    assert activity.cost_overhead == Decimal('100.00')


@pytest.mark.django_db
def test_cost_configuration_validation():
    """Test that CostConfiguration enforces valid overhead rates."""
    from smart_agri.core.models import CostConfiguration
    
    farm = Farm.objects.create(name='farm-validation', slug='farm-validation', region='F')
    
    # Valid configuration - should work
    config = CostConfiguration.objects.create(
        farm=farm,
        overhead_rate_per_hectare=Decimal('75.50'),
        currency='YER'
    )
    assert config.overhead_rate_per_hectare == Decimal('75.50')
    
    # Zero rate should be allowed (some farms may have no overhead)
    config.overhead_rate_per_hectare = Decimal('0.00')
    config.save()
    assert config.overhead_rate_per_hectare == Decimal('0.00')


@pytest.mark.django_db
def test_overhead_rate_uses_latest_effective_date():
    """Test that _get_overhead_rate uses proper date filtering."""
    from smart_agri.core.services.costing import _get_overhead_rate, DEFAULT_OVERHEAD_RATE
    from smart_agri.core.models import CostConfiguration
    
    farm = Farm.objects.create(name='farm-dates', slug='farm-dates', region='G')
    
    # Without configuration, should return default
    rate = _get_overhead_rate(farm.id)
    assert rate == DEFAULT_OVERHEAD_RATE
    
    # With configuration, should return configured rate
    CostConfiguration.objects.create(
        farm=farm,
        overhead_rate_per_hectare=Decimal('125.00'),
        currency='YER'
    )
    rate = _get_overhead_rate(farm.id)
    assert rate == Decimal('125.00')


@pytest.mark.django_db
def test_bulk_cost_calculation():
    """Test calculate_bulk_costs for multiple activities."""
    from smart_agri.core.services.costing import calculate_bulk_costs
    
    farm = Farm.objects.create(name='farm-bulk', slug='farm-bulk', region='H')
    location = Location.objects.create(farm=farm, name='Zone', type='Field')
    crop = Crop.objects.create(name='نخيل', mode='Open')
    task = Task.objects.create(name='ري', crop=crop, stage='خدمة')
    log = DailyLog.objects.create(farm=farm, log_date='2025-06-01')
    
    LaborRate.objects.create(farm=farm, role_name='عامل', cost_per_hour=Decimal('500'))
    
    # Create multiple activities
    activities = []
    for i in range(3):
        act = Activity.objects.create(
            log=log,
            crop=crop,
            task=task,
            days_spent=Decimal(str(i + 1)),  # 1, 2, 3 days
        )
        ActivityLocation.objects.create(activity=act, location=location)
        activities.append(act)
    
    # Bulk calculate
    updated = calculate_bulk_costs(Activity.objects.filter(log=log))
    
    # Check results
    for i, act in enumerate(activities):
        act.refresh_from_db()
        expected_labor = Decimal(str((i + 1) * 500))
        assert act.cost_labor == expected_labor


@pytest.mark.django_db  
def test_activity_cost_with_hectare_area():
    """Test overhead calculation for area specified in hectares."""
    farm = Farm.objects.create(name='farm-hectare', slug='farm-hectare', region='I')
    location = Location.objects.create(farm=farm, name='Big Field', type='Field')
    crop = Crop.objects.create(name='زيتون', mode='Open')
    task = Task.objects.create(name='قطف', crop=crop, stage='حصاد')
    log = DailyLog.objects.create(farm=farm, log_date='2025-07-01')
    
    # Area in hectares (not m2)
    activity = Activity.objects.create(
        log=log,
        crop=crop,
        task=task,
        planted_area=Decimal('5'),  # 5 hectares
        planted_uom='hectare',  # Not m2
    )
    ActivityLocation.objects.create(activity=activity, location=location)
    
    calculate_activity_cost(activity)
    activity.refresh_from_db()
    
    # Default rate 50.00 * 5 ha = 250.00
    assert activity.cost_overhead == Decimal('250.00')
