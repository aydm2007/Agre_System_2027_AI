from rest_framework.permissions import SAFE_METHODS
from rest_framework.throttling import SimpleRateThrottle


class FinancialMutationThrottle(SimpleRateThrottle):
    """Guard rate limiter for sensitive financial and inventory mutations."""

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
        ident = request.user.pk
        return self.cache_format % {"scope": self.scope, "ident": ident}
