import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smart_agri.config.settings')
django.setup()

from smart_agri.core.services.labor_estimation_service import LaborEstimationService

try:
    print("Testing LaborEstimationService with farm_id=4 and employees=[7, 12, 16, 13]")
    result = LaborEstimationService.preview_for_registered(farm_id=4, surrah_count=2, employee_ids=[7, 12, 16, 13])
    print("Success:", result)
except Exception as e:
    print("Error:", repr(e))
