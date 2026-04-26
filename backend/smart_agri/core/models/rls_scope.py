from django.db import DatabaseError, connection


def get_rls_user_id():
    """
    Resolve PostgreSQL session-scoped user id used by RLS tests/middleware.
    Returns None when no context is set or value is invalid.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.user_id', true)")
            raw_value = cursor.fetchone()[0]
    except (AttributeError, RuntimeError, DatabaseError):
        return None

    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None
