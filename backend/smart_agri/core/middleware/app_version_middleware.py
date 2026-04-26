from http import HTTPStatus

from django.conf import settings
from django.http import JsonResponse


def _parse_version(value):
    if not value:
        return ()
    parts = []
    for part in str(value).strip().split('.'):
        if not part:
            continue
        try:
            parts.append(int(part))
        except ValueError:
            break
        if len(parts) >= 3:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class AppVersionMiddleware:
    """
    Rejects API requests that come with an outdated client version,
    forcing the PWA to upgrade when the backend demands a new schema.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.current = _parse_version(getattr(settings, "APP_VERSION", "2.0.0"))
        self.min_allowed = _parse_version(getattr(settings, "APP_MIN_CLIENT_VERSION", settings.APP_VERSION))
        self.require_header = _parse_bool(getattr(settings, "APP_REQUIRE_VERSION_HEADER", True), default=True)
        self.public_exempt_paths = {
            "/api/v1/system-mode/",
        }

    def __call__(self, request):
        return self.get_response(request)
