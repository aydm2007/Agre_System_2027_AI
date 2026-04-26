
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from smart_agri.core.services.smart_context_service import SmartContextService
from drf_spectacular.utils import extend_schema, OpenApiParameter

class SuggestionView(APIView):
    """
    Agri-Guardian: Smart Context API.
    Provides predictive suggestions based on historical patterns.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get Smart Suggestions",
        description="Returns predicted activities based on -1 year history.",
        parameters=[
            OpenApiParameter("date", str, description="Target Date (YYYY-MM-DD)", required=True),
        ]
    )
    def get(self, request):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({"error": "Date required"}, status=400)
            
        suggestions = SmartContextService.get_suggestions(request.user, date_str)
        return Response({"suggestions": suggestions})
