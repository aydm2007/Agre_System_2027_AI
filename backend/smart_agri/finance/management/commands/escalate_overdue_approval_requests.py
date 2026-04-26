from django.core.management.base import BaseCommand

from smart_agri.finance.services.approval_service import ApprovalGovernanceService


class Command(BaseCommand):
    help = 'Escalate approval requests whose current stage exceeded its SLA.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        if options.get('dry_run'):
            count = ApprovalGovernanceService.overdue_queryset().count()
            self.stdout.write(self.style.WARNING(f'[dry-run] approval_requests_due_for_escalation={count}'))
            return
        count = ApprovalGovernanceService.escalate_overdue_requests()
        self.stdout.write(self.style.SUCCESS(f'approval_requests_escalated={count}'))
