from rest_framework.permissions import SAFE_METHODS
from rest_framework.throttling import SimpleRateThrottle, AnonRateThrottle


class FinancialMutationThrottle(SimpleRateThrottle):
    """Rate limit for authenticated mutating requests on sensitive endpoints."""

    scope = "financial_mutation"

    def allow_request(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if request.method in SAFE_METHODS:
            return None
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}


class AuthRateThrottle(AnonRateThrottle):
    """
    [AGRI-GUARDIAN] Dedicated throttle for login/refresh endpoints.
    Separate from the global AnonRateThrottle (100/day) to prevent
    login lockout when other anonymous traffic exhausts the daily quota.
    """
    scope = "auth_login"

