from django.core.management.base import BaseCommand

from smart_agri.finance.models import ApprovalRule
from smart_agri.finance.services.approval_service import ApprovalGovernanceService


class Command(BaseCommand):
    help = 'Report pending and overdue approval queues by role.'

    def handle(self, *args, **options):
        for role, _label in ApprovalRule.ROLE_CHOICES:
            qs = ApprovalGovernanceService.pending_for_role(role)
            pending = qs.count()
            overdue = sum(1 for req in qs if ApprovalGovernanceService.queue_snapshot(req=req)['is_overdue'])
            self.stdout.write(f'role={role} pending={pending} overdue={overdue}')
