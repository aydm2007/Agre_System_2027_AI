from datetime import date
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
import json

from smart_agri.core.models import Farm, Location, Crop, Task, DailyLog, CropPlan, CropVariety
from smart_agri.accounts.models import FarmMembership

class FixMultiLocationPayloadTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="fix_test_user", password="password", is_staff=True)
        self.client.force_authenticate(user=self.user)

        self.farm = Farm.objects.create(name="Test Farm", slug="test-farm", region="Test")
        FarmMembership.objects.create(user=self.user, farm=self.farm, role='Manager')
        
        self.location = Location.objects.create(name="Block 14", farm=self.farm)
        self.crop = Crop.objects.create(name="Banana", mode="Open", is_perennial=True)
        self.variety = CropVariety.objects.create(crop=self.crop, name="Variety 37")
        
        self.log = DailyLog.objects.create(farm=self.farm, log_date=date.today())
        
        self.plan = CropPlan.objects.create(
            farm=self.farm,
            name="Plan 2026",
            crop=self.crop,
            start_date=date.today(),
            end_date=date(2026, 12, 31)
        )
        # Link location to plan
        from smart_agri.core.models.planning import CropPlanLocation
        CropPlanLocation.objects.create(crop_plan=self.plan, location=self.location)

        self.task = Task.objects.create(
            crop=self.crop,
            name="Tree Maintenance",
            requires_tree_count=True,
            is_perennial_procedure=True
        )

    def test_locations_list_payload_maps_to_location_ids(self):
        """
        Verify that 'locations': [id] in payload is correctly mapped to 'location_ids' 
        in the serializer and processed by the service.
        """
        url = reverse('activities-list')
        payload = {
            "date": date.today().isoformat(),
            "farm": self.farm.id,
            "locations": [self.location.id],  # Frontend sends 'locations'
            "variety_id": self.variety.id,
            "crop_id": self.crop.id,
            "task_id": self.task.id,
            "log_id": self.log.id,
            "activity_tree_count": 100,
            "tree_count_delta": 0,
            "items": [] # Empty items should NOT trigger error
        }
        
        response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        
        # Before fix, this would fail with:
        # 1. location_ids required error
        # 2. items shortage/validation error
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        
        # Verify ActivityLocation was created
        from smart_agri.core.models.activity import ActivityLocation
        self.assertTrue(ActivityLocation.objects.filter(activity_id=response.data['id'], location_id=self.location.id).exists())
