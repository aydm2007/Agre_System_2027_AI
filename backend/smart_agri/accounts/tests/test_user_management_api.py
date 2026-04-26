import uuid
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from rest_framework.test import APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import Farm


class UserManagementApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_superuser(
            "root", "root@example.com", "pass123"
        )
        self.manager = User.objects.create_user(
            "manager", password="pass123", email="manager@example.com"
        )
        self.regular = User.objects.create_user(
            "regular", password="pass123", email="regular@example.com"
        )
        self.target = User.objects.create_user(
            "target", password="pass123", email="target@example.com"
        )

        self.farm = Farm.objects.create(name="Alpha Farm", slug="alpha", region="North")
        FarmMembership.objects.create(user=self.manager, farm=self.farm, role="مدير المزرعة")

        manager_group, _ = Group.objects.get_or_create(name="مدير المزرعة")
        self.manager.groups.add(manager_group)

    def test_assign_permission_success(self):
        permission = Permission.objects.get(codename="view_user")
        self.client.force_authenticate(self.superuser)

        response = self.client.post(
            f"/api/v1/auth/users/{self.target.id}/permissions/",
            {"permission_id": permission.id},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        self.assertEqual(response.status_code, 204)
        self.assertTrue(
            self.target.user_permissions.filter(id=permission.id).exists()
        )

    def test_assign_permission_invalid_id_rejected(self):
        self.client.force_authenticate(self.superuser)

        response = self.client.post(
            f"/api/v1/auth/users/{self.target.id}/permissions/",
            {"permission_id": 999999},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("permission_id", response.data)

    def test_add_to_group_success(self):
        self.client.force_authenticate(self.superuser)
        group = Group.objects.create(name="Supervisors")

        response = self.client.post(
            f"/api/v1/auth/users/{self.target.id}/groups/",
            {"group_id": group.id},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        self.assertEqual(response.status_code, 204)
        self.assertTrue(self.target.groups.filter(id=group.id).exists())

    def test_add_to_group_invalid_id_rejected(self):
        self.client.force_authenticate(self.superuser)

        response = self.client.post(
            f"/api/v1/auth/users/{self.target.id}/groups/",
            {"group_id": 987654},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("group_id", response.data)

    def test_regular_user_without_permission_blocked(self):
        self.client.force_authenticate(self.regular)

        response = self.client.get("/api/v1/auth/users/")

        self.assertEqual(response.status_code, 403)

    def test_manager_without_explicit_permission_allowed(self):
        self.client.force_authenticate(self.manager)

        response = self.client.get("/api/v1/auth/users/")

        self.assertEqual(response.status_code, 200)
        usernames = {item["username"] for item in response.data.get("results", [])}
        self.assertIn(self.manager.username, usernames)
