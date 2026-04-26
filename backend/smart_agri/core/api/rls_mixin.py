from smart_agri.core.models.rls_scope import get_rls_user_id

class RLSFarmScopedMixin:
    """
    [AGRI-GUARDIAN §Axis-6] Standardized RLS farm-scoping mixin.
    Apply to any ViewSet that operates on farm-linked data.
    """
    farm_field = 'farm'  # Override in subclass if needed
    
    def get_queryset(self):
        qs = super().get_queryset()
        rls_user_id = get_rls_user_id()
        if rls_user_id and rls_user_id != -1:
            lookup = f'{self.farm_field}__memberships__user_id'
            qs = qs.filter(**{lookup: rls_user_id}).distinct()
        return qs
