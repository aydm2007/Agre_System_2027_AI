
import pytest
from unittest.mock import Mock
from smart_agri.core.services.tree_inventory import TreeInventoryService
from smart_agri.core.models import Activity

@pytest.fixture
def mock_activity():
    """Create a mock activity with legacy and extension fields."""
    activity = Mock(spec=Activity)
    # Default everything to None
    activity.harvest_details = None
    activity.harvest_quantity = None
    activity.irrigation_details = None
    activity.water_volume = None
    activity.water_uom = 'm3'
    activity.material_details = None
    activity.fertilizer_quantity = None
    activity.fertilizer_uom = None
    return activity

@pytest.fixture
def mock_extension():
    """Create a mock extension object."""
    return Mock()

class TestTreeInventoryLegacyFields:
    """
    Test suite for TreeInventoryService legacy field helpers.
    Ensures safe handling of data from either new extension tables or legacy fields.
    """

    # --- Harvest Quantity Tests ---

    def test_get_harvest_quantity_extension_only(self, mock_activity, mock_extension):
        """Should prioritize extension field if present."""
        mock_extension.harvest_quantity = 100
        mock_activity.harvest_details = mock_extension
        mock_activity.harvest_quantity = 50 # Legacy field also present

        result = TreeInventoryService._get_harvest_quantity(mock_activity)
        assert result == 100

    def test_get_harvest_quantity_legacy_only(self, mock_activity):
        """Should fallback to legacy field if extension is missing."""
        mock_activity.harvest_details = None
        mock_activity.harvest_quantity = 50

        result = TreeInventoryService._get_harvest_quantity(mock_activity)
        assert result == 50

    def test_get_harvest_quantity_both_missing(self, mock_activity):
        """Should return None if neither field is present."""
        mock_activity.harvest_details = None
        mock_activity.harvest_quantity = None

        result = TreeInventoryService._get_harvest_quantity(mock_activity)
        assert result is None

    def test_get_harvest_quantity_extension_none_value(self, mock_activity, mock_extension):
        """Should return None if extension exists but value is None (and legacy is None)."""
        mock_extension.harvest_quantity = None
        mock_activity.harvest_details = mock_extension
        mock_activity.harvest_quantity = None

        result = TreeInventoryService._get_harvest_quantity(mock_activity)
        assert result is None
    
    # Note: Current implementation returns None from extension even if legacy has value?
    # Code: if ext: return ext.harvest_quantity
    # So if ext exists but quantity matches None, it returns None, IGNORING legacy.
    # This is an edge behavior to verify.
    def test_get_harvest_quantity_extension_none_blocks_legacy(self, mock_activity, mock_extension):
        """
        If extension record exists but has None, it SHOULD return None, 
        effectively masking legacy value (assuming extension is authoritative).
        """
        mock_extension.harvest_quantity = None
        mock_activity.harvest_details = mock_extension
        mock_activity.harvest_quantity = 999 

        result = TreeInventoryService._get_harvest_quantity(mock_activity)
        assert result is None

    # --- Water Volume Tests ---

    def test_get_water_volume_extension(self, mock_activity, mock_extension):
        mock_extension.water_volume = 500
        mock_activity.irrigation_details = mock_extension
        mock_activity.water_volume = 100

        result = TreeInventoryService._get_water_volume(mock_activity)
        assert result == 500

    def test_get_water_volume_legacy(self, mock_activity):
        mock_activity.irrigation_details = None
        mock_activity.water_volume = 100

        result = TreeInventoryService._get_water_volume(mock_activity)
        assert result == 100

    def test_get_water_volume_none(self, mock_activity):
        mock_activity.irrigation_details = None
        mock_activity.water_volume = None
        result = TreeInventoryService._get_water_volume(mock_activity)
        assert result is None

    # --- Water UOM Tests ---
    
    def test_get_water_uom_extension(self, mock_activity, mock_extension):
        mock_extension.uom = 'L'
        mock_activity.irrigation_details = mock_extension
        mock_activity.water_uom = 'm3'

        result = TreeInventoryService._get_water_uom(mock_activity)
        assert result == 'L'

    def test_get_water_uom_extension_none_defaults(self, mock_activity, mock_extension):
        """If extension exists but UOM is None, should default to 'm3' per code logic?"""
        # Code: if ext: return ext.uom or 'm3'
        mock_extension.uom = None
        mock_activity.irrigation_details = mock_extension
        
        result = TreeInventoryService._get_water_uom(mock_activity)
        assert result == 'm3'

    def test_get_water_uom_legacy(self, mock_activity):
        mock_activity.irrigation_details = None
        mock_activity.water_uom = 'Gallons'
        result = TreeInventoryService._get_water_uom(mock_activity)
        assert result == 'Gallons'

    def test_get_water_uom_legacy_default(self, mock_activity):
        mock_activity.irrigation_details = None
        mock_activity.water_uom = None # Or attribute missing handling
        # Code: getattr(activity, "water_uom", 'm3')
        # Here we mock getattr by setting it to None if we want, but getattr with default handles missing attr.
        # But if attr is None? getattr(obj, name, default) returns val if name exists.
        
        # If attribute exists and is None:
        mock_activity.water_uom = None
        # The code uses getattr(activity, 'water_uom', 'm3')
        # If activity.water_uom IS None, getattr returns None.
        # Wait, getattr(obj, 'attr', default) only returns default if 'attr' is NOT in obj.
        # If obj.attr = None, it returns None.
        # Let's check code: getattr(activity, 'water_uom', 'm3')
        # If we configure mock to have water_uom = None, it returns None.
        # If we configure mock to NOT have water_uom, it returns 'm3'.
        
        # Scenario 1: Attribute missing
        del mock_activity.water_uom
        result = TreeInventoryService._get_water_uom(mock_activity)
        assert result == 'm3'
        
    def test_get_water_uom_legacy_is_none(self, mock_activity):
        # Scenario 2: Attribute is None
        mock_activity.irrigation_details = None
        mock_activity.water_uom = None
        result = TreeInventoryService._get_water_uom(mock_activity)
        assert result is None 
        # Wait, if code is: getattr(activity, "water_uom", 'm3')
        # If activity has water_uom = None, it returns None.
        # If we want default, code should probably be (getattr(...) or 'm3').
        # Currently the test reflects CURRENT implementation behavior.

    # --- Fertilizer Quantity Tests ---

    def test_get_fertilizer_quantity_extension(self, mock_activity, mock_extension):
        mock_extension.fertilizer_quantity = 25.5
        mock_activity.material_details = mock_extension
        mock_activity.fertilizer_quantity = 10.0

        result = TreeInventoryService._get_fertilizer_quantity(mock_activity)
        assert result == 25.5

    def test_get_fertilizer_quantity_legacy(self, mock_activity):
        mock_activity.material_details = None
        mock_activity.fertilizer_quantity = 10.0

        result = TreeInventoryService._get_fertilizer_quantity(mock_activity)
        assert result == 10.0

