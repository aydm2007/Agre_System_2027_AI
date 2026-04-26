from django.core.management.base import BaseCommand

from smart_agri.finance.services.approval_service import ApprovalGovernanceService
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService
from smart_agri.core.services.remote_review_service import RemoteReviewService


class Command(BaseCommand):
    help = "Run approval escalation, attachment lifecycle queues, and remote-review drift reporting."

    def handle(self, *args, **options):
        escalated = ApprovalGovernanceService.escalate_overdue_requests()
        scanned = 0
        for attachment in AttachmentPolicyService.due_for_scan_queryset():
            AttachmentPolicyService.scan_attachment(attachment=attachment)
            attachment.save(update_fields=[
                "content_type", "malware_scan_status", "quarantine_reason", "quarantined_at", "scanned_at", "updated_at",
            ])
            scanned += 1
        archived = 0
        for attachment in AttachmentPolicyService.due_for_archive_queryset():
            AttachmentPolicyService.move_to_archive(attachment=attachment)
            attachment.save(update_fields=[
                "storage_tier", "archived_at", "archive_backend", "archive_key", "updated_at",
            ])
            archived += 1
        purged = 0
        for attachment in AttachmentPolicyService.due_for_purge_queryset():
            AttachmentPolicyService.purge_transient(attachment=attachment)
            attachment.save(update_fields=[
                "name", "content_type", "deleted_at", "deleted_by", "updated_at",
            ])
            purged += 1
        due_reviews = RemoteReviewService.report_due_reviews()
        self.stdout.write(self.style.SUCCESS(
            f"governance_maintenance: escalated={escalated}, scanned={scanned}, archived={archived}, purged={purged}, remote_due={len(due_reviews)}"
        ))
