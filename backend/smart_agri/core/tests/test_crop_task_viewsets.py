from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from smart_agri.core.api.viewsets.crop import CropViewSet, TaskViewSet
from smart_agri.core.models import Crop, Farm, Task
from smart_agri.core.models.crop import FarmCrop


class CropTaskViewSetSoftDeleteFilterTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(
            username="viewset-admin",
            password="secret123",
            is_superuser=True,
            is_staff=True,
        )
        self.farm = Farm.objects.create(
            name="Proof Farm",
            slug="proof-farm",
            region="تهامة",
        )
        self.active_crop = Crop.objects.create(name="Active Crop", mode="Open", is_perennial=False)
        self.stale_crop = Crop.objects.create(name="Stale Crop", mode="Open", is_perennial=True)
        FarmCrop.objects.create(farm=self.farm, crop=self.active_crop)
        self.stale_link = FarmCrop.objects.create(farm=self.farm, crop=self.stale_crop)
        self.stale_link.deleted_at = timezone.now()
        self.stale_link.save(update_fields=["deleted_at"])

        self.active_task = Task.objects.create(crop=self.active_crop, name="Active Task", stage="General")
        self.stale_task = Task.objects.create(crop=self.stale_crop, name="Stale Task", stage="General")

    def _call_list(self, viewset_cls, query):
        request = self.factory.get("/api/v1/proof/", query)
        force_authenticate(request, user=self.user)
        response = viewset_cls.as_view({"get": "list"})(request)
        self.assertEqual(response.status_code, 200)
        payload = response.data
        if isinstance(payload, dict) and "results" in payload:
            return payload["results"]
        return payload

    def test_crop_viewset_excludes_soft_deleted_farm_links(self):
        payload = self._call_list(CropViewSet, {"farm_id": self.farm.id})
        ids = {row["id"] for row in payload}
        self.assertIn(self.active_crop.id, ids)
        self.assertNotIn(self.stale_crop.id, ids)

    def test_task_viewset_excludes_soft_deleted_farm_links(self):
        payload = self._call_list(
            TaskViewSet,
            {"farm_id": self.farm.id, "crop": self.stale_crop.id},
        )
        self.assertEqual(payload, [])

        payload = self._call_list(
            TaskViewSet,
            {"farm_id": self.farm.id, "crop": self.active_crop.id},
        )
        ids = {row["id"] for row in payload}
        self.assertIn(self.active_task.id, ids)
        self.assertNotIn(self.stale_task.id, ids)
