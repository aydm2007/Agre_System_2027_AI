import pytest
from django.core.exceptions import ValidationError
from smart_agri.accounts.models import User
from smart_agri.core.models.farm import Farm
from smart_agri.finance.models import ApprovalRequest, ApprovalStageEvent

@pytest.mark.django_db
def test_same_user_cannot_approve_multiple_stages():
    """
    AGENTS Rule 20: Same actor must not clear more than one stage.
    """
    farm = Farm.objects.create(name="Test Farm")
    user = User.objects.create(username="multi_approver")
    
    req = ApprovalRequest.objects.create(
        farm=farm,
        module="TestModule",
        action="TestAction",
        requested_amount=1000,
        requested_by=user,
        total_stages=3,
        current_stage=1
    )
    
    # Simulate User A approving stage 1
    ApprovalStageEvent.objects.create(
        request=req,
        stage_number=1,
        actor=user,
        action_type='APPROVED'
    )
    
    # Attempt to approve stage 2 with the same user
    from smart_agri.finance.services.approval_service import ApprovalGovernanceService
    
    with pytest.raises(ValidationError) as exc:
        ApprovalGovernanceService.approve_request(user=user, request_id=req.id, note="Stage 2")
        
    assert "same actor" in str(exc.value).lower() or "already approved" in str(exc.value).lower() or "not allowed" in str(exc.value).lower()
