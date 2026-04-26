import pytest
from smart_agri.core.models.farm import Farm

@pytest.mark.django_db
def test_small_farm_escalation_when_review_overdue():
    """
    When RemoteReviewLog is missing for > 7 days on SMALL remote farm,
    RemoteReviewEscalation should be created.
    """
    pass
