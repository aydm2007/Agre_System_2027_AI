
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from smart_agri.core.services.traceability import TraceabilityService

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def batch_timeline(request, batch_number):
    """
    Returns the full audit trail for a specific batch.
    """
    if not batch_number:
        return Response({"error": "Batch number is mandatory"}, status=400)
    
    data = TraceabilityService.get_batch_timeline(batch_number)
    return Response(data)
