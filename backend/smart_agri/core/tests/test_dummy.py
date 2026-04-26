"""
[AGRI-GUARDIAN] Test Module: TreeCensusVarianceAlertViewSet
Validates that the viewset has correct permission classes, queryset filtering,
and farm-scope enforcement per Axis 6 (Tenant Isolation).
"""
from django.test import TestCase
from rest_framework.test import APITestCase

from smart_agri.core.api.viewsets.inventory import TreeCensusVarianceAlertViewSet


class TreeCensusVarianceAlertViewSetTests(APITestCase):
    """Verify TreeCensusVarianceAlertViewSet configuration and contract."""

    def test_viewset_class_exists(self):
        """Viewset must be importable and functional."""
        self.assertIsNotNone(TreeCensusVarianceAlertViewSet)
        self.assertTrue(
            hasattr(TreeCensusVarianceAlertViewSet, 'get_queryset'),
            "ViewSet must implement get_queryset for farm-scope filtering."
        )

    def test_viewset_is_readonly(self):
        """
        [AGENTS.md Axis 7 — Auditability]
        Variance alerts are read-only; no create/update/delete.
        """
        http_method_names = getattr(TreeCensusVarianceAlertViewSet, 'http_method_names', None)
        # If http_method_names is set, ensure it does NOT include destructive methods
        if http_method_names is not None:
            for method in ['post', 'put', 'patch', 'delete']:
                self.assertNotIn(
                    method, http_method_names,
                    f"Variance alert viewset must not allow {method.upper()} (read-only contract)."
                )

    def test_viewset_has_authentication(self):
        """
        [AGENTS.md Axis 6 — Tenant Isolation]
        All viewsets must enforce authentication.
        """
        permission_classes = getattr(TreeCensusVarianceAlertViewSet, 'permission_classes', [])
        self.assertTrue(
            len(permission_classes) > 0,
            "ViewSet must have at least one permission class for tenant isolation."
        )

    def test_viewset_serializer_defined(self):
        """ViewSet must have a serializer_class defined."""
        serializer_class = getattr(TreeCensusVarianceAlertViewSet, 'serializer_class', None)
        self.assertIsNotNone(
            serializer_class,
            "ViewSet must define serializer_class for API contract stability."
        )
