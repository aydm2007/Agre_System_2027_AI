from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from smart_agri.integration_hub.persistence import persistent_outbox_snapshot
from smart_agri.integration_hub.registry import integration_hub_snapshot
from smart_agri.core.services.attachment_policy_service import AttachmentPolicyService
from smart_agri.core.services.fixed_asset_workflow_service import FixedAssetWorkflowService
from smart_agri.core.services.fuel_reconciliation_service import FuelReconciliationService
from smart_agri.core.services.ops_health_service import OpsHealthService
from smart_agri.core.services.remote_review_service import RemoteReviewService
from smart_agri.finance.services.approval_service import ApprovalGovernanceService


class Command(BaseCommand):
    help = 'Generate JSON and Markdown release-readiness evidence snapshots.'

    def handle(self, *args, **options):
        payload = {
            'app_version': getattr(settings, 'APP_VERSION', 'unknown'),
            'debug': bool(getattr(settings, 'DEBUG', False)),
            'allowed_hosts_count': len(getattr(settings, 'ALLOWED_HOSTS', [])),
            'static_root': str(getattr(settings, 'STATIC_ROOT', '')),
            'media_root': str(getattr(settings, 'MEDIA_ROOT', '')),
            'cache_backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown'),
            'celery_broker_configured': bool(getattr(settings, 'CELERY_BROKER_URL', '')),
            'strict_farm_scope_headers': True if __import__('os').getenv('STRICT_FARM_SCOPE_HEADERS', 'false').lower() in {'1', 'true', 'yes', 'on'} else False,
            'integration_hub': integration_hub_snapshot(),
            'persistent_outbox': persistent_outbox_snapshot(),
            'outbox_health': OpsHealthService.integration_outbox_health_snapshot(),
            'attachment_runtime': AttachmentPolicyService.security_runtime_summary(),
            'attachment_runtime_health': OpsHealthService.attachment_runtime_health_snapshot(),
            'remote_review': RemoteReviewService.governance_snapshot(),
            'role_workbench': ApprovalGovernanceService.role_workbench_snapshot(),
            'runtime_governance': ApprovalGovernanceService.runtime_governance_snapshot(),
            'release_health': OpsHealthService.release_health_snapshot(),
            'fixed_assets': FixedAssetWorkflowService.runtime_summary(),
            'fuel_reconciliation': FuelReconciliationService.runtime_summary(),
        }
        target = Path(settings.BASE_DIR) / 'release_readiness_snapshot.json'
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        md_target = Path(settings.BASE_DIR) / 'release_readiness_snapshot.md'
        md_target.write_text(
            '# Release Readiness Snapshot\n\n'
            f"- app_version: `{payload['app_version']}`\n"
            f"- debug: `{payload['debug']}`\n"
            f"- allowed_hosts_count: `{payload['allowed_hosts_count']}`\n"
            f"- celery_broker_configured: `{payload['celery_broker_configured']}`\n"
            f"- strict_farm_scope_headers: `{payload['strict_farm_scope_headers']}`\n"
            f"- integration publisher: `{payload['integration_hub'].get('publisher', 'unknown')}`\n"
            f"- outbox total: `{payload['persistent_outbox'].get('total', 0)}`\n"
            f"- outbox queued: `{payload['persistent_outbox'].get('counts', {}).get('pending', 0)}`\n"
            f"- outbox dispatched: `{payload['persistent_outbox'].get('counts', {}).get('dispatched', 0)}`\n"
            f"- outbox failed_retryable: `{payload['persistent_outbox'].get('counts', {}).get('failed', 0)}`\n"
            f"- outbox dead_letter_count: `{payload['persistent_outbox'].get('dead_letter_count', 0)}`\n"
            f"- outbox severity: `{payload['outbox_health'].get('severity', 'unknown')}`\n"
            f"- attachment lifecycle events: `{payload['attachment_runtime'].get('lifecycle_events', 0)}`\n"
            f"- attachment quarantined: `{payload['attachment_runtime'].get('quarantined', 0)}`\n"
            f"- attachment health severity: `{payload['attachment_runtime_health'].get('severity', 'unknown')}`\n"
            f"- remote due reviews: `{payload['remote_review'].get('due_count', 0)}`\n"
            f"- role_workbench_rows: `{len(payload['role_workbench'].get('rows', []))}`\n",
            encoding='utf-8',
        )
        self.stdout.write(self.style.SUCCESS(f'Wrote {target} and {md_target}'))
