"""
[AGRI-GUARDIAN] Unified Exception Handler.
Provides consistent JSON error responses across all API endpoints.

Response Format:
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
- Offline Doctrine: Error codes parseable by client retry logic
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────
# Error Code Registry — domain-specific error codes for structured handling
# ──────────────────────────────────────────────────────────────────────────

ERROR_CODES = {
    'VALIDATION_ERROR': 'خطأ في المدخلات',
    'NOT_FOUND': 'العنصر غير موجود',
    'PERMISSION_DENIED': 'ليس لديك صلاحية لتنفيذ هذا الإجراء',
    'AUTHENTICATION_FAILED': 'فشل التحقق من الهوية',
    'THROTTLED': 'تجاوزت الحد المسموح. حاول مجدداً بعد قليل',
    'IDEMPOTENCY_REPLAY': 'تم تنفيذ هذا الطلب مسبقاً',
    'FISCAL_PERIOD_CLOSED': 'الفترة المالية مغلقة — لا يمكن إجراء تعديلات',
    'INSUFFICIENT_STOCK': 'الرصيد غير كافي',
    'FARM_SCOPE_VIOLATION': 'انتهاك نطاق المزرعة',
    'DECIMAL_REQUIRED': 'القيم العشرية من النوع float مرفوضة. استعمل Decimal',
    'INTERNAL_ERROR': 'خطأ داخلي في الخادم',
}


def _classify_error_code(exc, status_code):
    """Map exception/status to a domain-specific error code."""
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


def _extract_details(response_data):
    """Extract structured field-level details from DRF response data."""
    if isinstance(response_data, dict):
        details = {}
        for key, value in response_data.items():
            if key in ('detail', 'error'):
                continue
            details[key] = value if isinstance(value, list) else [str(value)]
        return details
    if isinstance(response_data, list):
        return {'non_field_errors': response_data}
    return {}


def custom_exception_handler(exc, context):
    """
    [AGRI-GUARDIAN] Global Exception Handler.
    
    1. Converts Django's ValidationErrors into structured 400 responses.
    2. Wraps all DRF errors in a consistent {error: {code, message, details}} format.
    3. Catches unhandled 500 exceptions with safe JSON payloads.
    
    Registered in settings.py as:
        REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'smart_agri.core.exceptions.custom_exception_handler'
    """
    # Let DRF handle it first (covers HTTP errors, throttling, auth, etc.)
    response = exception_handler(exc, context)

    # Case 1: DRF handled it → wrap in structured format
    if response is not None:
        error_code = _classify_error_code(exc, response.status_code)
        
        # Extract the best message
        message = ''
        if isinstance(response.data, dict):
            message = str(response.data.get('detail', ''))
        if not message:
            message = ERROR_CODES.get(error_code, str(exc))

        response.data = {
            'error': {
                'code': error_code,
                'message': message,
                'details': _extract_details(response.data) if isinstance(response.data, dict) else {},
            }
        }

        # Log server errors
        if response.status_code >= 500:
            view_name = getattr(context.get('view'), '__class__', type(None)).__name__
            logger.error(
                f"[AGRI-GUARDIAN] Server error: {error_code} — {message}",
                exc_info=exc,
                extra={'view': view_name},
            )

        return response

    # Case 2: Django ValidationError (not handled by DRF)
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, 'message_dict'):
            details = exc.message_dict
            message = next(iter(exc.message_dict.values()), [str(exc)])[0] if exc.message_dict else str(exc)
        elif hasattr(exc, 'messages'):
            details = {'non_field_errors': exc.messages}
            message = exc.messages[0] if exc.messages else str(exc)
        else:
            details = {}
            message = str(exc)

        error_code = _classify_error_code(exc, 400)
        logger.warning(f"[AGRI-GUARDIAN] ValidationError: {error_code} — {message}")

        return Response(
            {
                'error': {
                    'code': error_code,
                    'message': message,
                    'details': details,
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Case 3: Unhandled exception → safe 500 response
    view_name = getattr(context.get('view'), '__class__', type(None)).__name__
    logger.error(
        f"[AGRI-GUARDIAN] Unhandled exception [{view_name}]: {type(exc).__name__} — {exc}",
        exc_info=True,
    )

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
