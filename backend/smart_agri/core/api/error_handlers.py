"""
[AGRI-GUARDIAN] Unified API Error Handler.
Provides a consistent error response format across all endpoints.

Format:
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "الرسالة بالعربي",
        "details": {...}
    }
}

Compliance:
- AGENTS.md §27: StandardError formatting
- Axis 7: Audit-safe error responses (no stack traces in production)
- Offline Doctrine: Error codes must be parseable by client retry logic
"""
import logging
import traceback
from rest_framework.views import exception_handler
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────
# Error Code Registry
# ──────────────────────────────────────────────────────────────────────────

ERROR_CODES = {
    'VALIDATION_ERROR': 'خطأ في المدخلات',
    'NOT_FOUND': 'العنصر غير موجود',
    'PERMISSION_DENIED': 'ليس لديك صلاحية لتنفيذ هذا الإجراء',
    'AUTHENTICATION_FAILED': 'فشل التحقق من الهوية',
    'THROTTLED': 'تجاوزت الحد المسموح. حاول مجدداً بعد قليل',
    'IDEMPOTENCY_REPLAY': 'تم تنفيذ هذا الطلب مسبقاً (معاد تشغيله)',
    'FISCAL_PERIOD_CLOSED': 'الفترة المالية مغلقة — لا يمكن إجراء تعديلات',
    'INSUFFICIENT_STOCK': 'الرصيد غير كافي',
    'FARM_SCOPE_VIOLATION': 'انتهاك نطاق المزرعة',
    'DECIMAL_REQUIRED': 'القيم العشرية من النوع float مرفوضة. استعمل Decimal',
    'INTERNAL_ERROR': 'خطأ داخلي في الخادم',
}


def agri_exception_handler(exc, context):
    """
    Custom DRF exception handler that returns consistent JSON error responses.
    
    Usage in settings.py:
        REST_FRAMEWORK = {
            'EXCEPTION_HANDLER': 'smart_agri.core.api.error_handlers.agri_exception_handler',
        }
    """
    # Let DRF handle it first
    response = exception_handler(exc, context)

    if response is not None:
        error_code = _classify_error_code(exc, response.status_code)
        error_message = _extract_message(exc, response)

        response.data = {
            'error': {
                'code': error_code,
                'message': error_message,
                'details': _extract_details(exc, response),
            }
        }

        # Log server errors
        if response.status_code >= 500:
            logger.error(
                f"[AGRI-GUARDIAN] Server error: {error_code} — {error_message}",
                exc_info=exc,
                extra={
                    'view': str(context.get('view', '')),
                    'request_method': context.get('request', {}).method if context.get('request') else 'N/A',
                }
            )

        return response

    # Unhandled exceptions — return 500 with safe message
    if isinstance(exc, DjangoValidationError):
        from rest_framework.response import Response
        return Response(
            {
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': str(exc.message) if hasattr(exc, 'message') else str(exc),
                    'details': exc.message_dict if hasattr(exc, 'message_dict') else {},
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Log unexpected errors
    logger.error(
        f"[AGRI-GUARDIAN] Unhandled exception: {type(exc).__name__} — {exc}",
        exc_info=True,
        extra={'view': str(context.get('view', ''))},
    )

    from rest_framework.response import Response
    return Response(
        {
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': ERROR_CODES['INTERNAL_ERROR'],
                'details': {},
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _classify_error_code(exc, status_code):
    """Map exception/status to an error code from the registry."""
    exc_msg = str(exc).lower()

    # Domain-specific classification
    if 'idempotenc' in exc_msg:
        return 'IDEMPOTENCY_REPLAY'
    if 'fiscal' in exc_msg or 'مغلقة' in exc_msg or 'closed' in exc_msg:
        return 'FISCAL_PERIOD_CLOSED'
    if 'رصيد' in exc_msg or 'insufficient' in exc_msg or 'stock' in exc_msg:
        return 'INSUFFICIENT_STOCK'
    if 'float' in exc_msg or 'decimal' in exc_msg:
        return 'DECIMAL_REQUIRED'
    if 'انتهاك أمني' in exc_msg or 'farm_id' in exc_msg:
        return 'FARM_SCOPE_VIOLATION'

    # Status-based fallback
    code_map = {
        400: 'VALIDATION_ERROR',
        401: 'AUTHENTICATION_FAILED',
        403: 'PERMISSION_DENIED',
        404: 'NOT_FOUND',
        429: 'THROTTLED',
    }
    return code_map.get(status_code, 'INTERNAL_ERROR')


def _extract_message(exc, response):
    """Extract a human-readable Arabic message from the exception."""
    # If the original response has detail, use it
    if isinstance(response.data, dict):
        detail = response.data.get('detail', '')
        if detail:
            return str(detail)

    # Try the exception message
    msg = str(exc)
    if msg and len(msg) < 500:
        return msg

    # Fallback to registry
    code = _classify_error_code(exc, response.status_code)
    return ERROR_CODES.get(code, ERROR_CODES['INTERNAL_ERROR'])


def _extract_details(exc, response):
    """Extract structured error details for field-level validation errors."""
    if isinstance(response.data, dict):
        # DRF returns {field: [errors]} for validation errors
        details = {}
        for key, value in response.data.items():
            if key == 'detail':
                continue
            details[key] = value if isinstance(value, list) else [str(value)]
        return details if details else {}
    if isinstance(response.data, list):
        return {'non_field_errors': response.data}
    return {}
