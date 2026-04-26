import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.settings')
django.setup()

from smart_agri.core.api.viewsets.labor_estimation import LaborEstimatePreviewSerializer
from smart_agri.core.services.labor_estimation_service import LaborEstimationService

payload = {
    "farm_id": 3,
    "labor_entry_mode": "REGISTERED",
    "surrah_count": "1.0000",
    "period_hours": "8.0000",
    "employee_ids": [7]
}

serializer = LaborEstimatePreviewSerializer(data=payload)
if serializer.is_valid():
    try:
        LaborEstimationService.preview_for_registered(**serializer.validated_data)
        print("Success!")
    except Exception as e:
        print(f"Service Error: {e.detail if hasattr(e, 'detail') else e}")
else:
    print(f"Serializer Error: {serializer.errors}")
