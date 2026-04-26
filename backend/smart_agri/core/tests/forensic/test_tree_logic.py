
import pytest
from unittest.mock import Mock
from smart_agri.core.models import Activity, LocationTreeStock, TreeStockEvent
from smart_agri.core.services.tree_inventory import TreeEventCalculator

class TestTreeEventCalculatorForensic:
    """
    Forensic Logic Tests for TreeEventCalculator.
    Verifies the mathematical and logical integrity of the inventory brain.
    PURE LOGIC ONLY - NO DATABASE.
    """

    @pytest.fixture
    def calculator(self):
        return TreeEventCalculator()

    @pytest.fixture
    def mock_activity(self):
        a = Mock(spec=Activity)
        a.task = None
        a.pk = 100
        a.tree_count_delta = 0
        a.harvest_quantity = None
        a.harvest_details = None
        a.water_volume = None
        a.fertilizer_quantity = None
        a.tree_loss_reason = None
        return a

    # --- Event Type Determination ---

    def test_compute_event_planting(self, calculator, mock_activity):
        """Positive delta -> PLANTING"""
        delta = 500
        event_type = calculator.compute_event_type(mock_activity, delta)
        assert event_type == TreeStockEvent.PLANTING

    def test_compute_event_loss(self, calculator, mock_activity):
        """Negative delta -> LOSS"""
        delta = -10
        event_type = calculator.compute_event_type(mock_activity, delta)
        assert event_type == TreeStockEvent.LOSS

    def test_compute_event_transfer(self, calculator, mock_activity):
        """Stock changed flag -> TRANSFER"""
        delta = 50
        event_type = calculator.compute_event_type(mock_activity, delta, stock_changed=True)
        assert event_type == TreeStockEvent.TRANSFER

    def test_compute_event_harvest(self, calculator, mock_activity):
        """Harvest Task -> HARVEST (regardless of delta usually, but logic checks task)"""
        mock_task = Mock()
        mock_task.is_harvest_task = True
        mock_activity.task = mock_task
        
        event_type = calculator.compute_event_type(mock_activity, delta=0)
        assert event_type == TreeStockEvent.HARVEST

    def test_compute_event_adjustment(self, calculator, mock_activity):
        """Zero delta, no special task -> ADJUSTMENT (or None if not tracked?)"""
        # Logic says: if delta=0, check water/fert, else Adjustment.
        # Check source code: if delta=0... 
        # Source checks water/fert -> Adjustment.
        # Fallback -> Adjustment.
        
        event_type = calculator.compute_event_type(mock_activity, delta=0)
        assert event_type == TreeStockEvent.ADJUSTMENT

    # --- Resulting Count Math (The Critical Path) ---

    def test_resolve_resulting_count_simple_add(self, calculator, mock_activity):
        """Base stock + Delta"""
        mock_stock = Mock(spec=LocationTreeStock)
        mock_stock.current_tree_count = 100
        
        # New activity being created
        count = calculator.resolve_resulting_count(
            activity=mock_activity,
            stock=mock_stock,
            existing_event=None,
            activity_tree_count_change=50, # New calculation style
            previous_activity_tree_count=None
        )
        assert count == 150 # 100 + 50

    def test_resolve_resulting_count_legacy_override(self, calculator, mock_activity):
        """Explicit activity.activity_tree_count overrides stock calculation (Legacy mode)"""
        mock_activity.activity_tree_count = 999
        mock_stock = Mock(spec=LocationTreeStock)
        mock_stock.current_tree_count = 100
        
        # If existing_event is present, it might trigger the override logic
        mock_event = Mock(spec=TreeStockEvent)
        
        count = calculator.resolve_resulting_count(
            activity=mock_activity,
            stock=mock_stock,
            existing_event=mock_event,
            activity_tree_count_change=None,
            previous_activity_tree_count=None
        )
        # Assuming legacy logic: if activity.activity_tree_count is set AND existing event...
        # Code: if activity.activity_tree_count is not None and (existing_event ...): return activity_tree_count
        assert count == 999

    def test_resolve_resulting_count_delta_update(self, calculator, mock_activity):
        """Updating existing event: Base = Previous Result. Result = Base + Change."""
        # Scenario: Analysis of delta logic
        # self.resolve_resulting_count arguments in source:
        # activity_tree_count_change -> This is the effective/net change? 
        # Actually in source: return base + activity_tree_count_change
        # where base = previous_activity... or existing_event.resulting... or stock.current...
        
        mock_stock = Mock(spec=LocationTreeStock)
        mock_stock.current_tree_count = 1000
        
        mock_event = Mock(spec=TreeStockEvent)
        mock_event.resulting_tree_count = 1000 # Snapshot at that time
        
        # We are calculating what the count WOULD be if we applied change?
        # Or is 'activity_tree_count_change' the delta?
        # Let's verify line 265: return base + activity_tree_count_change
        
        count = calculator.resolve_resulting_count(
            activity=mock_activity,
            stock=mock_stock,
            existing_event=mock_event,
            activity_tree_count_change=-5,
            previous_activity_tree_count=None
        )
        assert count == 995 # 1000 - 5

