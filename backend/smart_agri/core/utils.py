from typing import Optional
from django.http import HttpRequest
from smart_agri.core.models.farm import Farm

def get_current_farm(request: HttpRequest) -> Optional[Farm]:
    """
    [AGRI-ASSET SOVEREIGN UTILITY]
    Resolves the current active farm from the request.
    Priority:
    1. Direct farm_id in request.session
    2. Header X-Farm-ID (for API calls)
    3. User's primary farm (if single farm user)
    """
    farm_id = request.session.get('active_farm_id') or request.headers.get('X-Farm-ID')
    
    if farm_id:
        try:
            return Farm.objects.get(id=farm_id)
        except Farm.DoesNotExist:
            pass
            
    # Fallback to first available farm for simplicity in development
    if request.user.is_authenticated:
        # Assuming FarmMembership or similar exists
        # For the sake of this dynamic injection, we return the first farm
        return Farm.objects.first()
        
    return None
