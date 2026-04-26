from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run the operational governance maintenance cycle for approvals, remote reviews, and evidence lifecycle.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = bool(options.get('dry_run'))
        self.stdout.write('running=scan_pending_attachments')
        call_command('scan_pending_attachments', **({'dry_run': True} if dry_run else {}))
        self.stdout.write('running=report_approval_workqueues')
        call_command('report_approval_workqueues')
        self.stdout.write('running=escalate_overdue_approval_requests')
        call_command('escalate_overdue_approval_requests', **({'dry_run': True} if dry_run else {}))
        self.stdout.write('running=report_due_remote_reviews')
        call_command('report_due_remote_reviews')
        self.stdout.write('running=enforce_due_remote_reviews')
        call_command('enforce_due_remote_reviews', **({'dry_run': True} if dry_run else {}))
        self.stdout.write('running=archive_due_attachments')
        call_command('archive_due_attachments', **({'dry_run': True} if dry_run else {}))
        self.stdout.write('running=purge_expired_transient_attachments')
        call_command('purge_expired_transient_attachments', **({'dry_run': True} if dry_run else {}))
        if dry_run:
            self.stdout.write(self.style.SUCCESS('governance_maintenance_cycle=dry_run_completed'))
            return
        self.stdout.write(self.style.SUCCESS('governance_maintenance_cycle=completed'))
