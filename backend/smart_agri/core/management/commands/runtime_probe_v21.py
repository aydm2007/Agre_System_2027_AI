from django.core.management.base import BaseCommand

from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService
from smart_agri.core.services.ops_health_service import OpsHealthService
from smart_agri.core.services.remote_review_service import RemoteReviewService
from smart_agri.finance.services.approval_service import ApprovalGovernanceService


class Command(BaseCommand):
    help = 'Emit a governed runtime snapshot for V21 readiness proof.'

    def handle(self, *args, **options):
        payload = {
            'maintenance': ApprovalGovernanceService.maintenance_summary(),
            'runtime_governance': ApprovalGovernanceService.runtime_governance_snapshot(),
            'role_workbench': ApprovalGovernanceService.role_workbench_snapshot(),
            'remote_review': RemoteReviewService.governance_snapshot(),
            'attachment_runtime': AttachmentPolicyService.security_runtime_summary(),
            'outbox_health': OpsHealthService.integration_outbox_health_snapshot(),
            'attachment_runtime_health': OpsHealthService.attachment_runtime_health_snapshot(),
            'release_health': OpsHealthService.release_health_snapshot(),
        }
        self.stdout.write(self.style.SUCCESS('runtime_probe_v21_ready'))
        self.stdout.write(str(payload))
