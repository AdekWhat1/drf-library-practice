from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

REGISTER_URL = reverse("user:create")
TOKEN_URL = reverse("user:token_obtain_pair")
ME_URL = reverse("user:manage")


class PublicUserApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        payload = {
            "email": "test@example.com",
            "password": "password123",
            "first_name": "Test",
            "last_name": "User",
        }
        response = self.client.post(REGISTER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", response.data)

    def test_create_user_password_too_short(self):
        payload = {
            "email": "test@example.com",
            "password": "123",
        }
        response = self.client.post(REGISTER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(email=payload["email"]).exists()
        self.assertFalse(user_exists)

    def test_create_user_with_existing_email_fails(self):
        payload = {
            "email": "test@example.com",
            "password": "password123",
        }
        get_user_model().objects.create_user(**payload)

        response = self.client.post(REGISTER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_obtain_token_success(self):
        payload = {
            "email": "test@example.com",
            "password": "password123",
        }
        get_user_model().objects.create_user(**payload)

        response = self.client.post(TOKEN_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_unauthorized_user_cannot_access_me(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@example.com",
            password="password123",
            first_name="Initial",
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "id": self.user.id,
                "email": self.user.email,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "is_staff": False,
            },
        )

    def test_update_profile_first_name(self):
        payload = {"first_name": "Updated"}
        response = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.first_name, payload["first_name"])

    def test_update_password_success(self):
        payload = {"password": "newpassword123"}
        response = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.check_password(payload["password"]))
