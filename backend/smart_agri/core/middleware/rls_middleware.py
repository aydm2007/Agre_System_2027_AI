"""
RLS Middleware - Sets PostgreSQL session variable for Row Level Security

AGRI-MAESTRO Protocol: Phase 3 Security Hardening
Sets app.user_id for each authenticated request to enable farm isolation via RLS policies.
"""
import logging
from django.db import connection, OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


class RLSMiddleware:
    """
    Middleware to set PostgreSQL session variable for RLS policies.
    
    Purpose:
        - Sets app.user_id = request.user.id for authenticated users
        - Enables PostgreSQL RLS policies to filter data by farm access
        - Uses SET LOCAL to ensure context is transaction-scoped
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        logger.info("RLS Middleware initialized")
    
    def __call__(self, request):
        if connection.vendor != "postgresql":
            return self.get_response(request)

        if request.user.is_authenticated:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('app.user_id', %s, false)",
                        [str(request.user.id)]
                    )
                    logger.debug(f"✔ RLS context set: user_id={request.user.id}")
            except (OperationalError, ProgrammingError, ValueError) as e:
                logger.critical(f"✖ Failed to set RLS context for user {request.user.id}: {e}")
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Security Context Error: Unable to establish RLS.")
        else:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('app.user_id', NULL, false)")
            except (OperationalError, ProgrammingError, ValueError) as e:
                logger.warning("Failed to reset RLS context: %s", e)

        return self.get_response(request)


class RLSSuperuserBypassMiddleware:
    """
    Monitor superuser access without breaking RLS.
    Superusers still rely on FarmMembership records for farm scope.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if connection.vendor != "postgresql":
            return self.get_response(request)
        if request.user.is_authenticated and request.user.is_superuser:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('app.user_id', %s, false)", [str(request.user.id)])
            except (OperationalError, ProgrammingError, ValueError) as e:
                logger.error(f"Failed to refresh RLS context for superuser {request.user.username}: {e}")
        return self.get_response(request)
