"""
[AGRI-GUARDIAN] Server-Sent Events (SSE) for Real-Time Notifications.

Provides a lightweight push channel for:
- Variance alerts
- Approval inbox updates
- Offline queue sync status
- Fiscal period warnings

No extra infrastructure needed (no Redis Pub/Sub, no WebSocket).
Works behind load balancers and CDN proxies.
"""
import json
import time
import logging
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


def _resolve_stream_user(request):
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        return user

    access_token = request.GET.get('access_token') or request.GET.get('token')
    auth_header = request.headers.get('Authorization', '')
    bearer_token = auth_header.split(' ', 1)[1] if auth_header.startswith('Bearer ') else None
    candidate_token = access_token or bearer_token
    if not candidate_token:
        return None

    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(candidate_token)
        user = jwt_auth.get_user(validated_token)
        request.user = user
        return user
    except (AuthenticationFailed, InvalidToken, TokenError, ValueError):
        logger.info('notifications.stream.auth_failed')
        return None


def _event_stream(user, farm_id=None):
    """
    Generator that yields SSE-formatted events.
    Each event is a JSON payload with type and data.
    """
    # Initial connection event
    yield _format_sse({
        'type': 'connected',
        'user': user.username,
        'farm_id': farm_id,
        'timestamp': _now_iso(),
    })

    # Poll for new notifications every 15 seconds
    last_check = time.time()
    heartbeat_interval = 15  # seconds
    max_duration = 300  # 5 minutes max connection

    start = time.time()
    while (time.time() - start) < max_duration:
        elapsed = time.time() - last_check
        if elapsed >= heartbeat_interval:
            last_check = time.time()

            # Check for pending variance alerts
            alerts = _check_variance_alerts(user, farm_id)
            if alerts:
                yield _format_sse({
                    'type': 'variance_alert',
                    'count': len(alerts),
                    'alerts': alerts[:5],  # Latest 5
                    'timestamp': _now_iso(),
                })

            # Check for pending approvals
            approvals = _check_pending_approvals(user)
            if approvals > 0:
                yield _format_sse({
                    'type': 'approval_pending',
                    'count': approvals,
                    'timestamp': _now_iso(),
                })

            for ops_alert in _ops_alerts(user=user, farm_id=farm_id):
                logger.info(
                    'ops.alert.emitted',
                    extra={
                        'fingerprint': ops_alert.get('fingerprint'),
                        'kind': ops_alert.get('kind'),
                        'severity': ops_alert.get('severity'),
                        'farm_id': ops_alert.get('farm_id'),
                        'request_id': ops_alert.get('request_id'),
                        'correlation_id': ops_alert.get('correlation_id'),
                    },
                )
                yield _format_sse({
                    'type': ops_alert.get('kind'),
                    **ops_alert,
                    'timestamp': _now_iso(),
                })

            # Heartbeat to keep connection alive
            yield _format_sse({
                'type': 'heartbeat',
                'timestamp': _now_iso(),
            })

        time.sleep(1)

    # Final event before closing
    yield _format_sse({
        'type': 'disconnected',
        'reason': 'max_duration_reached',
        'timestamp': _now_iso(),
    })


def _format_sse(data, event=None):
    """Format data as SSE event string."""
    lines = []
    if event:
        lines.append(f'event: {event}')
    lines.append(f'data: {json.dumps(data, ensure_ascii=False)}')
    lines.append('')  # Blank line terminates event
    return '\n'.join(lines) + '\n'


def _now_iso():
    from django.utils import timezone
    return timezone.now().isoformat()


def _check_variance_alerts(user, farm_id=None):
    """Check for recent unacknowledged variance alerts."""
    try:
        from smart_agri.core.models import MaterialVarianceAlert
        from smart_agri.core.api.permissions import user_farm_ids

        qs = MaterialVarianceAlert.objects.filter(
            resolved_at__isnull=True,
        ).order_by('-created_at')

        if not user.is_superuser:
            farm_ids = user_farm_ids(user)
            if farm_id:
                farm_ids = [int(farm_id)] if int(farm_id) in farm_ids else []
            qs = qs.filter(crop_plan__farm_id__in=farm_ids)

        alerts = list(qs.values('id', 'status', 'note')[:5])
        return alerts
    except (ValueError, TypeError, LookupError, AttributeError, ImportError, RuntimeError):
        logger.debug("Variance alerts check skipped", exc_info=True)
        return []


def _check_pending_approvals(user):
    """Check count of pending approval items for user."""
    try:
        from smart_agri.core.models import AuditLog
        count = AuditLog.objects.filter(
            action='PENDING_APPROVAL',
        ).count()
        return count
    except (ValueError, TypeError, LookupError, AttributeError, ImportError, RuntimeError):
        logger.debug("Approval check skipped", exc_info=True)
        return 0


def _approval_runtime_attention():
    try:
        from smart_agri.finance.services.approval_service import ApprovalGovernanceService

        snapshot = ApprovalGovernanceService.runtime_governance_snapshot()
        if snapshot.get('blocked_requests') or snapshot.get('overdue_requests'):
            return {
                'severity': snapshot.get('severity', 'attention'),
                'blocked_requests': snapshot.get('blocked_requests', 0),
                'overdue_requests': snapshot.get('overdue_requests', 0),
                'pending_requests': snapshot.get('pending_requests', 0),
                'blocked_reasons': snapshot.get('blocked_reasons', {}),
            }
    except (ValueError, TypeError, LookupError, AttributeError, ImportError, RuntimeError):
        logger.debug("Approval runtime attention skipped", exc_info=True)
    return None


def _attachment_runtime_attention():
    try:
        from smart_agri.core.services.ops_health_service import OpsHealthService

        snapshot = OpsHealthService.attachment_runtime_health_snapshot()
        if snapshot.get('pending_scan') or snapshot.get('quarantined'):
            return {
                'severity': snapshot.get('severity', 'attention'),
                'pending_scan': snapshot.get('pending_scan', 0),
                'quarantined': snapshot.get('quarantined', 0),
                'due_archive': snapshot.get('due_archive', 0),
                'risk_flags': snapshot.get('authoritative_evidence_risk_flags', []),
            }
    except (ValueError, TypeError, LookupError, AttributeError, ImportError, RuntimeError):
        logger.debug("Attachment runtime attention skipped", exc_info=True)
    return None


def _outbox_runtime_attention():
    try:
        from smart_agri.core.services.ops_health_service import OpsHealthService

        snapshot = OpsHealthService.integration_outbox_health_snapshot()
        if snapshot.get('dead_letter_count') or snapshot.get('stale_pending_count'):
            return {
                'severity': snapshot.get('severity', 'attention'),
                'dead_letter_count': snapshot.get('dead_letter_count', 0),
                'stale_pending_count': snapshot.get('stale_pending_count', 0),
                'retry_ready_count': snapshot.get('retry_ready_count', 0),
            }
    except (ValueError, TypeError, LookupError, AttributeError, ImportError, RuntimeError):
        logger.debug("Outbox runtime attention skipped", exc_info=True)
    return None


def _release_health_warning():
    try:
        from smart_agri.core.services.ops_health_service import OpsHealthService

        snapshot = OpsHealthService.release_health_snapshot()
        if snapshot.get('severity') != 'healthy':
            return {
                'severity': snapshot.get('severity', 'attention'),
                'stale_warning_count': snapshot.get('stale_warning_count', 0),
                'warnings': snapshot.get('warnings', [])[:5],
            }
    except (ValueError, TypeError, LookupError, AttributeError, ImportError, RuntimeError):
        logger.debug("Release health warning skipped", exc_info=True)
    return None


def _ops_alerts(*, user, farm_id=None):
    try:
        from smart_agri.core.services.ops_alert_service import OpsAlertService

        resolved_farm_id = None
        if farm_id not in (None, '', 'all'):
            try:
                resolved_farm_id = int(farm_id)
            except (TypeError, ValueError):
                resolved_farm_id = None
        snapshot = OpsAlertService.alerts_snapshot(
            user=user,
            farm_id=resolved_farm_id,
            include_acknowledged=False,
            limit=20,
        )
        return snapshot.get('items', [])
    except (ValueError, TypeError, LookupError, AttributeError, ImportError, RuntimeError):
        logger.debug("Ops alerts check skipped", exc_info=True)
        return []


@require_GET
def notifications_stream(request):
    """
    SSE endpoint for real-time notifications.

    Usage:
        const evtSource = new EventSource('/api/v1/notifications/stream/');
        evtSource.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'variance_alert') { ... }
        };
    """
    user = _resolve_stream_user(request)
    if not user:
        return JsonResponse(
            {
                'detail': 'يتطلب هذا التدفق جلسة مصادقة صالحة.',
                'code': 'AUTHENTICATION_REQUIRED',
            },
            status=401,
            json_dumps_params={'ensure_ascii': False},
        )

    farm_id = request.GET.get('farm_id') or request.GET.get('farm')

    response = StreamingHttpResponse(
        _event_stream(user, farm_id),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Nginx: disable buffering
    return response
