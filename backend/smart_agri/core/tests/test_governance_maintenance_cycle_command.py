from io import StringIO
from unittest.mock import call, patch

from django.core.management import call_command
from django.test import SimpleTestCase


class GovernanceMaintenanceCycleCommandTests(SimpleTestCase):
    @patch("smart_agri.core.management.commands.run_governance_maintenance_cycle.call_command")
    def test_cycle_forwards_dry_run_to_mutating_subcommands(self, mocked_call_command):
        out = StringIO()

        call_command("run_governance_maintenance_cycle", "--dry-run", stdout=out)

        self.assertEqual(
            mocked_call_command.call_args_list,
            [
                call("scan_pending_attachments", dry_run=True),
                call("report_approval_workqueues"),
                call("escalate_overdue_approval_requests", dry_run=True),
                call("report_due_remote_reviews"),
                call("enforce_due_remote_reviews", dry_run=True),
                call("archive_due_attachments", dry_run=True),
                call("purge_expired_transient_attachments", dry_run=True),
            ],
        )
        self.assertIn("governance_maintenance_cycle=dry_run_completed", out.getvalue())
